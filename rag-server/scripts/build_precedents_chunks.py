"""
민사법 판결문(precedents) 데이터 소스용 청크+임베딩 생성 스크립트.

설계 근거: /home/janghyeon/claude/RawRagProject.md
"판결문(precedents) 데이터 소스 — 청크 생성 방식" 섹션 참고.

사용법:
    .venv/bin/python scripts/build_precedents_chunks.py --limit 100 --seed 42
    .venv/bin/python scripts/build_precedents_chunks.py            # 전체 처리(재시작 가능)
"""

import argparse
import asyncio
import glob
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ollama_client import OllamaClient  # noqa: E402

SOURCE_DIR = (
    "/home/janghyeon/01.민사법 LLM 사전학습 및 Instruction Tuning 데이터/"
    "3.개방데이터/1.데이터/Validation/02.라벨링데이터/"
    "VL_01. 민사법_001. 판결문_0001. 질의응답"
)

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUT_PATH = os.path.join(OUT_DIR, "precedents_chunks.jsonl")
LOG_PATH = os.path.join(OUT_DIR, "build_log.txt")

TAG_PAT = re.compile(r"<(삭제|이미지\d*-?\d*|각주\d*|주소)>")
HEADER_PAT = re.compile(r"^\s*\d+\.\s*\S")

SECTION_LIMIT = 3000
SUBCHUNK_TARGET = 1000


def clean(text: str) -> str:
    return TAG_PAT.sub("", text)


def split_sections(sentences: list[str]) -> list[tuple[str, list[str]]]:
    header_idx = [
        i for i, s in enumerate(sentences)
        if HEADER_PAT.match(s.strip()) and len(s.strip()) <= 30
    ]
    if not header_idx:
        return [("(전체)", sentences)]
    bounds = header_idx + [len(sentences)]
    return [
        (sentences[a].strip(), sentences[a:b])
        for a, b in zip(header_idx, bounds[1:])
    ]


def build_chunks(title: str, sents: list[str]) -> list[str]:
    full = clean("".join(sents))
    if len(full) <= SECTION_LIMIT:
        return [full]
    chunks, buf, buflen = [], [], 0
    for s in sents:
        cs = clean(s)
        buf.append(cs)
        buflen += len(cs)
        if buflen >= SUBCHUNK_TARGET:
            chunks.append("".join(buf))
            buf, buflen = [], 0
    if buf:
        chunks.append("".join(buf))
    return [f"[{title}] {c}" for c in chunks]


def load_processed_doc_ids() -> set[str]:
    if not os.path.exists(OUT_PATH):
        return set()
    done = set()
    with open(OUT_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                done.add(json.loads(line)["doc_id"])
            except Exception:
                continue
    return done


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


async def main() -> None:
    global OUT_PATH, LOG_PATH

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="처리할 문서 수 제한(샘플 검증용)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--embed-model", default="bge-m3")
    parser.add_argument("--out", default=None, help="출력 jsonl 경로(기본: data/precedents_chunks.jsonl)")
    parser.add_argument("--source-dir", default=None, help="원본 JSON 폴더 경로(기본: 스크립트 내 SOURCE_DIR, PC마다 경로가 다르면 지정)")
    parser.add_argument("--shard-count", type=int, default=1, help="여러 PC로 나눠 돌릴 때 전체 대수")
    parser.add_argument("--shard-index", type=int, default=0, help="이 PC가 맡을 샤드 번호(0부터, shard-count보다 작아야 함)")
    args = parser.parse_args()

    if args.out:
        OUT_PATH = args.out
        LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(args.out)), "build_log.txt")
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    source_dir = args.source_dir or SOURCE_DIR
    files = sorted(glob.glob(os.path.join(source_dir, "*.json")))
    if args.shard_count > 1:
        files = [f for i, f in enumerate(files) if i % args.shard_count == args.shard_index]
    if args.limit is not None:
        random.seed(args.seed)
        files = random.sample(files, min(args.limit, len(files)))

    processed = load_processed_doc_ids()
    ollama = OllamaClient(args.ollama_url, args.embed_model)
    await ollama.ensure_embed_model_available()

    total_docs = len(files)
    done_docs = 0
    skipped_docs = 0
    total_chunks = 0
    t_start = time.time()

    log(f"시작: 대상 문서 {total_docs}개 (이미 처리됨 {len(processed)}건은 건너뜀)")

    with open(OUT_PATH, "a", encoding="utf-8") as out_f:
        for fp in files:
            doc_id_probe = None
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                info = data.get("info", {})
                doc_id = info.get("doc_id") or os.path.basename(fp)
                doc_id_probe = doc_id
                if doc_id in processed:
                    skipped_docs += 1
                    continue

                sentences = data.get("taskinfo", {}).get("sentences", [])
                sections = split_sections(sentences)

                doc_chunk_count = 0
                for title, sents in sections:
                    pieces = build_chunks(title, sents)
                    for idx, text in enumerate(pieces):
                        if not text.strip():
                            continue
                        embedding = await ollama.embed(text)
                        record = {
                            "text": text,
                            "embedding": embedding,
                            "doc_id": doc_id,
                            "normalized_court": info.get("normalized_court"),
                            "announce_date": info.get("announce_date"),
                            "casenames": info.get("casenames"),
                            "casetype": info.get("casetype"),
                            "section_title": title,
                            "sub_chunk_index": idx,
                        }
                        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        out_f.flush()
                        doc_chunk_count += 1

                total_chunks += doc_chunk_count
                done_docs += 1

                if done_docs % 10 == 0 or done_docs == total_docs:
                    elapsed = time.time() - t_start
                    rate = done_docs / elapsed if elapsed > 0 else 0
                    remaining = (total_docs - done_docs - skipped_docs) / rate if rate > 0 else 0
                    log(
                        f"진행 {done_docs}/{total_docs} (건너뜀 {skipped_docs}) "
                        f"| 누적 청크 {total_chunks} | 경과 {elapsed:.0f}s "
                        f"| 예상 잔여 {remaining:.0f}s"
                    )
            except Exception as e:
                log(f"오류 (doc_id={doc_id_probe}, file={fp}): {e!r}")

    log(f"완료: 문서 {done_docs}건 처리, {skipped_docs}건 건너뜀, 총 청크 {total_chunks}개")


if __name__ == "__main__":
    asyncio.run(main())
