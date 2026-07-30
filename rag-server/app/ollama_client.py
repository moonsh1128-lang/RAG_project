import httpx


class OllamaClient:
    def __init__(self, base_url: str, embed_model: str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120)
        self._embed_model = embed_model

    async def list_models(self) -> list[str]:
        response = await self._client.get("/api/tags")
        response.raise_for_status()
        return [m["name"] for m in response.json()["models"]]

    async def ensure_embed_model_available(self) -> None:
        models = await self.list_models()
        # 태그는 "bge-m3:latest"처럼 붙어 나오므로 설정값이 접두어로 들어있는지로 확인
        if not any(m == self._embed_model or m.startswith(f"{self._embed_model}:") for m in models):
            raise RuntimeError(
                f"Ollama({self._client.base_url})에 임베딩 모델 '{self._embed_model}'이 없음. "
                f"설치된 모델: {models}"
            )

    async def embed(self, text: str) -> list[float]:
        response = await self._client.post(
            "/api/embed", json={"model": self._embed_model, "input": text}
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]
