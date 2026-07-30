import asyncio
import json
import uuid

CHUNK_SIZE = 20  # 질문 텍스트를 이 글자 수만큼씩 나눠 보낸다


class ApiServerClient:
    """API Server와의 커넥션 하나 = 세션 하나. session_id는 연결 시점에 1회 생성해 재사용한다.

    백그라운드로 커넥션을 계속 읽어, 서버가 보내는 ping에는 즉시 pong으로 응답하고
    나머지(질의 응답)는 큐에 넣는다 — 그래야 send_query() 응답을 기다리는 동안이 아니라
    사용자가 입력 중일 때도 ping에 응답할 수 있다.
    """

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self.session_id = str(uuid.uuid4())
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._responses: asyncio.Queue[dict] = asyncio.Queue()
        self._reader_task: asyncio.Task | None = None
        self._closed_event = asyncio.Event()

    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        self._reader_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        try:
            while line := await self._reader.readline():
                message = json.loads(line)
                if message.get("type") == "ping":
                    await self._write({"type": "pong"})
                    continue
                await self._responses.put(message)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        finally:
            self._closed_event.set()

    async def _write(self, payload: dict) -> None:
        self._writer.write((json.dumps(payload, ensure_ascii=False) + "\n").encode())
        await self._writer.drain()

    async def _wait_for_response(self) -> dict:
        get_response = asyncio.create_task(self._responses.get())
        connection_closed = asyncio.create_task(self._closed_event.wait())
        try:
            done, pending = await asyncio.wait(
                {get_response, connection_closed}, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            if get_response in done:
                return get_response.result()
            raise ConnectionError("API Server와의 연결이 끊어짐")
        finally:
            get_response.cancel()
            connection_closed.cancel()

    async def send_query(self, rag_selector_query: str, question: str) -> dict:
        # small(1)번부터 big(N)번까지 순서대로 청크를 만든다
        chunks = [question[i : i + CHUNK_SIZE] for i in range(0, len(question), CHUNK_SIZE)] or [""]
        final_request_number = len(chunks)

        response: dict | None = None
        for request_number, message_chunk in enumerate(chunks, start=1):
            payload = {
                "session_id": self.session_id,
                "request_number": request_number,
                "message_chunk": message_chunk,
                "is_complete": request_number == final_request_number,
            }
            if request_number == 1:
                payload["rag_selector_query"] = rag_selector_query
                payload["final_request_number"] = final_request_number

            await self._write(payload)
            response = await self._wait_for_response()

        return response

    async def close(self) -> None:
        self._reader_task.cancel()
        self._writer.close()
        await self._writer.wait_closed()
