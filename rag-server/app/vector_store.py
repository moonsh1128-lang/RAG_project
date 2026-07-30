from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    embedding: list[float]


@dataclass
class SearchHit:
    chunk: Chunk
    score: float


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


class VectorStore:
    """청크 수가 적어(테스트용 가상 데이터) 완전탐색으로 충분하다."""

    def __init__(self, chunks: list[Chunk]):
        self._chunks = chunks

    def search(self, query_embedding: list[float], top_k: int) -> list[SearchHit]:
        hits = [
            SearchHit(chunk, _cosine(query_embedding, chunk.embedding))
            for chunk in self._chunks
        ]
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:top_k]
