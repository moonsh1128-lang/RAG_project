import httpx

CHUNK_SIZE = 20  # MainServer/RagServer 프로토콜은 그대로라, 여기서 이 글자 수만큼씩 나눠 보낸다


class MainServerClient:
    def __init__(self, base_url: str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120)

    async def query(
        self,
        session_id: str,
        rag_selector_query: str,
        question: str,
        message_count: int,
        history: list[dict],
    ) -> dict:
        # small(1)번부터 big(N)번까지 순서대로 청크를 만들어 MainServer의 기존 청크 프로토콜 그대로 호출.
        chunks = [question[i : i + CHUNK_SIZE] for i in range(0, len(question), CHUNK_SIZE)] or [""]
        final_request_number = len(chunks)

        result: dict | None = None
        for request_number, message_chunk in enumerate(chunks, start=1):
            payload = {
                "session_id": session_id,
                "request_number": request_number,
                "message_chunk": message_chunk,
                "is_complete": request_number == final_request_number,
            }
            if request_number == 1:
                payload["rag_selector_query"] = rag_selector_query
                payload["final_request_number"] = final_request_number
                payload["message_count"] = message_count
                payload["history"] = history

            response = await self._client.post("/query", json=payload)
            response.raise_for_status()
            result = response.json()

        return result

    async def complaint(self, payload: dict) -> dict:
        response = await self._client.post("/complaint", json=payload)
        response.raise_for_status()
        return response.json()
