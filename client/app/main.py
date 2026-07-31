import asyncio
import os
import uuid

from app.api_server_client import ApiServerClient

HOST = os.environ.get("API_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("API_SERVER_PORT", "9000"))


async def run_complaint_flow(client: ApiServerClient, loop: asyncio.AbstractEventLoop) -> None:
    async def ask(prompt: str) -> str:
        return (await loop.run_in_executor(None, input, prompt)).strip()

    complainant_name = await ask("고소인 명칭(회사명 또는 성명)> ")
    complainant_representative = await ask("고소인 대표자(개인이면 빈 줄)> ")
    complainant_address = await ask("고소인 주소> ")
    accused_name = await ask("피고소인 성명> ")
    accused_address = await ask("피고소인 주소> ")
    charge = await ask("죄명> ")
    incident_description = await ask("사건 설명(육하원칙으로)> ")

    response = await client.send_complaint(
        {
            "complainant_name": complainant_name,
            "complainant_representative": complainant_representative,
            "complainant_address": complainant_address,
            "accused_name": accused_name,
            "accused_address": accused_address,
            "charge": charge,
            "incident_description": incident_description,
        }
    )

    document = response.get("document")
    if document is None:
        print(f"생성 실패: {response}")
        return

    # client를 실행한 현재 작업 디렉터리에 저장한다(패키지 설치 위치 등이 아니라).
    filepath = os.path.join(os.getcwd(), f"고소장_{uuid.uuid4().hex[:8]}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(document)
    print(f"저장됨: {filepath}")


async def main() -> None:
    client = ApiServerClient(HOST, PORT)
    await client.connect()
    print(f"연결됨 (session_id={client.session_id}). 빈 줄 입력 시 종료.")
    loop = asyncio.get_running_loop()
    try:
        while True:
            # input()은 블로킹 호출이라 그대로 쓰면 사용자가 입력하는 동안
            # 이벤트 루프가 멈춰 백그라운드 ping 응답이 안 됨 — executor로 뺀다.
            rag_selector_query = (
                await loop.run_in_executor(None, input, "질문(또는 /고소장 입력)> ")
            ).strip()
            if not rag_selector_query:
                break
            if rag_selector_query == "/고소장":
                await run_complaint_flow(client, loop)
                continue
            question = (await loop.run_in_executor(None, input, "실제 질문> ")).strip()
            response = await client.send_query(rag_selector_query, question)
            print(response)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
