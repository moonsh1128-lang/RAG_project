import asyncio
import os

from app.api_server_client import ApiServerClient

HOST = os.environ.get("API_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("API_SERVER_PORT", "9000"))


async def main() -> None:
    client = ApiServerClient(HOST, PORT)
    await client.connect()
    print(f"연결됨 (session_id={client.session_id}). 빈 줄 입력 시 종료.")
    loop = asyncio.get_running_loop()
    try:
        while True:
            # input()은 블로킹 호출이라 그대로 쓰면 사용자가 입력하는 동안
            # 이벤트 루프가 멈춰 백그라운드 ping 응답이 안 됨 — executor로 뺀다.
            rag_selector_query = (await loop.run_in_executor(None, input, "Rag 선택 질문> ")).strip()
            if not rag_selector_query:
                break
            question = (await loop.run_in_executor(None, input, "실제 질문> ")).strip()
            response = await client.send_query(rag_selector_query, question)
            print(response)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
