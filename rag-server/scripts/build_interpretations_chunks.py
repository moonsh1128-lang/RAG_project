"""
민사법 유권해석(interpretations) 데이터 소스용 청크+임베딩 생성 스크립트.

판결문/법령과 다른 점: 문서 자체가 짧고(평균 1,142자, 최대 3,147자) "질의/갑설·을설/회시"로
이미 하나의 완결된 질의응답 단위라 섹션 분할이 필요 없음 — 문서 1개 = 청크 1개.

사용법:
    .venv/bin/python scripts/build_interpretations_chunks.py --source-dir "<유권해석 JSON 폴더>" --out "<출력 jsonl 경로>"
"""

import argparse
import asyncio
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ollama_client import OllamaClient  # noqa: E402

DEFAULT_SOURCE_DIR = (
    "/home/janghyeon/01.민사법 LLM 사전학습 및 Instruction Tuning 데이터/"
    "3.개방데이터/1.데이터/Validation/02.라벨링데이터/"
    "VL_01. 민사법_004. 유권해석_0001. 질의응답"
)

TAG_PAT = re.compile(r"<[^<>]{1,20}>")


def clean(text: str) -> str:
    return TAG_PAT.sub("", text)


def normalize_text(sentences) -> str:
    joined = sentences if isinstance(sentences, str) else "".join(sentences)
    return clean(joined)


def load_processed_doc_ids(out_path: str) -> set[str]:
    if not os.path.exists(out_path):
        return set()
    done = set()
    with open(out_path, encoding="utf-8") as f:
        for line in f:
            try:
                done.add(json.loads(line)["doc_id"])
            except Exception:
                continue
    return done


def log(log_path: str, msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--out", required=True, help="출력 jsonl 경로")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--embed-model", default="bge-m3")
    args = parser.parse_args()

    out_path = args.out
    log_path = os.path.join(os.path.dirname(os.path.abspath(out_path)), "build_log.txt")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    files = sorted(glob.glob(os.path.join(args.source_dir, "*.json")))
    processed = load_processed_doc_ids(out_path)
    ollama = OllamaClient(args.ollama_url, args.embed_model)
    await ollama.ensure_embed_model_available()

    total_chunks = 0
    t_start = time.time()
    log(log_path, f"시작: 유권해석 파일 {len(files)}개 (이미 처리됨 {len(processed)}건은 건너뜀)")

    with open(out_path, "a", encoding="utf-8") as out_f:
        for fp in files:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            info = data.get("info", {})
            doc_id = info.get("doc_id") or os.path.basename(fp)
            if doc_id in processed:
                continue

            text = normalize_text(data.get("taskinfo", {}).get("sentences", ""))
            if not text.strip():
                continue

            embedding = await ollama.embed(text)
            record = {
                "text": text,
                "embedding": embedding,
                "doc_id": doc_id,
                "response_institute": info.get("response_institute"),
                "response_date": info.get("response_date"),
                "title": info.get("title"),
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()
            total_chunks += 1

            elapsed = time.time() - t_start
            log(log_path, f"완료: {doc_id} | 누적 {total_chunks} | 경과 {elapsed:.0f}s")

    log(log_path, f"전체 완료: 총 {total_chunks}개 청크 생성")


if __name__ == "__main__":
    asyncio.run(main())
