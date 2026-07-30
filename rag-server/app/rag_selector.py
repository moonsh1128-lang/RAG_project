from app.ollama_client import OllamaClient

RAG_SOURCES = {
    "precedents": "민사법 판결문",
    "statutes": "민사법 법령",
    "adjudications": "민사법 심결례",
    "interpretations": "민사법 유권해석",
}

_anchor_embeddings: dict[str, list[float]] | None = None


async def _anchors(ollama: OllamaClient) -> dict[str, list[float]]:
    global _anchor_embeddings
    if _anchor_embeddings is None:
        _anchor_embeddings = {
            key: await ollama.embed(desc) for key, desc in RAG_SOURCES.items()
        }
    return _anchor_embeddings


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


async def select_rag(ollama: OllamaClient, rag_type_message: str) -> str:
    anchors = await _anchors(ollama)
    query_embedding = await ollama.embed(rag_type_message)
    return max(anchors, key=lambda key: _cosine(query_embedding, anchors[key]))
