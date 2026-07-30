import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.channel import JsonMessageChannel
from app.chunk_assembly import ChunkAssembly
from app.ollama_client import OllamaClient
from app.rag_selector import RAG_SOURCES, select_rag
from app.rag_sources import preload_real_data, retrieve

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-server")

ollama = OllamaClient(
    base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
    embed_model=os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3"),
)

# 청크 1(RagType 포함)에서 결정된 Rag를 이후 청크들도 찾아갈 수 있도록 세션 단위로 기억한다.
session_to_rag: dict[str, str] = {}
# Rag(=RagChannel)마다 session_id -> 그 세션의 청크 모음
assemblies_by_rag: dict[str, dict[str, ChunkAssembly]] = {key: {} for key in RAG_SOURCES}


async def handle_chunk(payload: dict) -> dict:
    """하나의 RagChannel 안에서 실행되는 처리 — 청크를 모으고, 완성되면 합쳐서 검색한다."""
    session_id = payload["SessionId"]
    target_rag = session_to_rag[session_id]
    assemblies = assemblies_by_rag[target_rag]
    assembly = assemblies.setdefault(session_id, ChunkAssembly())

    assembly.add(payload["RequestNumber"], payload["MessageChunk"], payload.get("FinalRequestNumber"))

    if not assembly.is_ready(payload["IsComplete"]):
        return {"IsFinal": False}

    message = assembly.assemble()
    started_at = time.perf_counter()
    rag_context = await retrieve(ollama, target_rag, message)
    retrieval_time_ms = round((time.perf_counter() - started_at) * 1000)

    del assemblies[session_id]
    del session_to_rag[session_id]

    return {
        "IsFinal": True,
        "SelectRag": target_rag,
        "message": message,
        "RagContext": rag_context,
        "RetrievalTimeMs": retrieval_time_ms,
    }


rag_channels: dict[str, JsonMessageChannel] = {key: JsonMessageChannel(handle_chunk) for key in RAG_SOURCES}


@asynccontextmanager
async def lifespan(app: FastAPI):
    models = await ollama.list_models()
    logger.info("이 PC의 Ollama에서 발견한 모델: %s", models)
    await ollama.ensure_embed_model_available()
    preload_real_data()
    for channel in rag_channels.values():
        channel.start()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/rag")
async def process_rag_chunk(payload: dict) -> dict:
    session_id = payload["SessionId"]

    if payload["RequestNumber"] == 1:
        # 첫 청크에만 RagType이 실려온다 — 여기서 결정해 이후 청크가 갈 RagChannel을 정한다.
        session_to_rag[session_id] = await select_rag(ollama, payload["RagType"])

    return await rag_channels[session_to_rag[session_id]].submit(payload)
