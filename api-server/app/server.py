import asyncio
import json
import os

from app.main_server_client import MainServerClient

HOST = os.environ.get("API_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("API_SERVER_PORT", "9000"))
MAIN_SERVER_URL = os.environ.get("MAIN_SERVER_URL", "http://localhost:8080")

PING_INTERVAL_SEC = 10
MAX_MISSED_PONGS = 3

main_server = MainServerClient(MAIN_SERVER_URL)

# session_id -> 그 세션을 물고 있는 커넥션의 writer. MainServer 응답은 커넥션이 아니라
# 이 registry로 session_id를 찾아 해당 client에게 전달한다.
sessions: dict[str, asyncio.StreamWriter] = {}


class ConnectionState:
    def __init__(self, writer: asyncio.StreamWriter):
        self.writer = writer
        self.session_id: str | None = None
        self.awaiting_pong = False
        self.missed_pongs = 0


async def ping_loop(state: ConnectionState) -> None:
    """PING_INTERVAL_SEC마다 ping을 보내고, MAX_MISSED_PONGS번 연속 pong이 없으면 연결을 끊는다."""
    try:
        while True:
            await asyncio.sleep(PING_INTERVAL_SEC)

            if state.awaiting_pong:
                state.missed_pongs += 1
                if state.missed_pongs >= MAX_MISSED_PONGS:
                    print(f"[핑퐁 {MAX_MISSED_PONGS}회 미수신] session_id={state.session_id} 연결 종료")
                    state.writer.close()
                    return

            state.awaiting_pong = True
            state.writer.write(b'{"type": "ping"}\n')
            await state.writer.drain()
    except (ConnectionError, OSError):
        return


async def process_query(payload: dict, state: ConnectionState) -> None:
    """MainServer 호출은 오래 걸릴 수 있어 별도 태스크로 돌린다 — 그래야 이 쿼리를 기다리는
    동안에도 같은 커넥션의 read loop가 막히지 않고 pong을 계속 받을 수 있다."""
    session_id = payload.get("session_id")
    if session_id is not None:
        sessions[session_id] = state.writer

    try:
        if payload.get("type") == "complaint":
            result = await main_server.complaint(payload)
        else:
            # MainServer가 LLMServer 응답을 그대로 돌려주므로 결과를 그대로 전달한다.
            result = await main_server.query(payload)
    except Exception as exc:
        result = {"error": str(exc)}

    target = sessions.get(session_id, state.writer)
    try:
        target.write((json.dumps(result, ensure_ascii=False) + "\n").encode())
        await target.drain()
    except (ConnectionError, OSError):
        pass  # 그 사이 클라이언트가 이미 끊겼으면 조용히 버린다


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    print(f"[연결] {peer}")
    state = ConnectionState(writer)
    pinger = asyncio.create_task(ping_loop(state))
    query_tasks: set[asyncio.Task] = set()
    try:
        # 한 커넥션 = 한 세션. 줄바꿈으로 구분된 JSON 메시지를 계속 받아 처리한다.
        while line := await reader.readline():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                writer.write(b'{"error": "invalid JSON"}\n')
                await writer.drain()
                continue

            if payload.get("type") == "pong":
                state.awaiting_pong = False
                state.missed_pongs = 0
                continue

            state.session_id = payload.get("session_id")
            task = asyncio.create_task(process_query(payload, state))
            query_tasks.add(task)
            task.add_done_callback(query_tasks.discard)
    finally:
        pinger.cancel()
        for task in query_tasks:
            task.cancel()
        if state.session_id is not None and sessions.get(state.session_id) is writer:
            del sessions[state.session_id]
        writer.close()
        await writer.wait_closed()
        print(f"[종료] {peer}")


async def main() -> None:
    server = await asyncio.start_server(handle_client, HOST, PORT)
    print(f"API Server 대기 중: {HOST}:{PORT} (MainServer: {MAIN_SERVER_URL})")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
