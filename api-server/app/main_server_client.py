import httpx


class MainServerClient:
    def __init__(self, base_url: str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120)

    async def query(self, payload: dict) -> dict:
        response = await self._client.post("/query", json=payload)
        response.raise_for_status()
        return response.json()

    async def complaint(self, payload: dict) -> dict:
        response = await self._client.post("/complaint", json=payload)
        response.raise_for_status()
        return response.json()
