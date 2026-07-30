from app.mock_data import MOCK_DOCUMENTS
from app.ollama_client import OllamaClient
from app.vector_store import Chunk, VectorStore

_stores: dict[str, VectorStore] = {}


async def _store_for(ollama: OllamaClient, selected_rag: str) -> VectorStore:
    if selected_rag not in _stores:
        texts = MOCK_DOCUMENTS.get(selected_rag)
        if texts is None:
            raise ValueError(f"알 수 없는 Rag: {selected_rag}")
        chunks = [Chunk(text, await ollama.embed(text)) for text in texts]
        _stores[selected_rag] = VectorStore(chunks)
    return _stores[selected_rag]


async def retrieve(ollama: OllamaClient, selected_rag: str, message: str) -> str:
    store = await _store_for(ollama, selected_rag)
    query_embedding = await ollama.embed(message)
    hits = store.search(query_embedding, top_k=1)
    return hits[0].chunk.text if hits else "(관련 내용 없음)"
