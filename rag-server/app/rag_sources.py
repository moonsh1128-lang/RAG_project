import json
import logging

from app.mock_data import MOCK_DOCUMENTS
from app.ollama_client import OllamaClient
from app.vector_store import Chunk, VectorStore

logger = logging.getLogger("rag-server")

# 실 데이터가 준비된 Rag만 여기 있음 — 아직 없는 Rag(예: statutes)는 mock_data.py로 대체
REAL_DATA_FILES = {
    "precedents": "/home/janghyeon/claude/rag-system/RagFile/precedents_chunks.jsonl",
    "interpretations": "/home/janghyeon/claude/rag-system/RagFile2/interpretations_chunks.jsonl",
    "adjudications": "/home/janghyeon/claude/rag-system/RagFile3/adjudications_chunks.jsonl",
}

_stores: dict[str, VectorStore] = {}


def _load_real_chunks(selected_rag: str) -> list[Chunk]:
    chunks = []
    with open(REAL_DATA_FILES[selected_rag], encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            if selected_rag == "precedents" and record.get("casetype") != "civil":
                continue
            chunks.append(Chunk(record["text"], record["embedding"]))
    return chunks


def preload_real_data() -> None:
    """서버 시작 시 실 데이터를 미리 읽어둔다 — 요청 중간에 대용량 파일 파싱으로 지연되지 않도록."""
    for selected_rag in REAL_DATA_FILES:
        chunks = _load_real_chunks(selected_rag)
        _stores[selected_rag] = VectorStore(chunks)
        logger.info("%s 실 데이터 로드: %d개 청크", selected_rag, len(chunks))


async def _store_for(ollama: OllamaClient, selected_rag: str) -> VectorStore:
    if selected_rag not in _stores:
        # 실 데이터가 없는 Rag(현재 statutes)는 가상 샘플을 그때그때 임베딩해 대체
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
