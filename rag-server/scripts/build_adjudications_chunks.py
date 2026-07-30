"""
민사법 심결례(adjudications) 데이터 소스용 청크+임베딩 생성 스크립트.

판결문과 다른 점: 숫자 헤더("1. 2. 3.")가 거의 없음(279개 중 1개뿐) — 대신
"진정요지/사건개요/당사자의 주장/관련 규정/인정사실/판단/결론/주문" 같은
번호 없는 단어형 소제목이 짧은 단독 줄로 등장. 그래서 정규식 대신 키워드 사전으로
섹션 경계를 감지한다. 오버사이즈(3,000자 초과) 재분할 정책은 판결문과 동일.

사용법:
    .venv/bin/python scripts/build_adjudications_chunks.py --source-dir "<심결례 JSON 폴더>" --out "<출력 jsonl 경로>"
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
    "VL_01. 민사법_003. 심결례_0001. 질의응답"
)

TAG_PAT = re.compile(r"<[^<>]{1,20}>")
HEADER_KEYWORDS = ["규정", "법령", "인정사실", "판단", "결론", "주장", "요지", "개요", "취지", "주문"]
SECTION_LIMIT = 3000
SUBCHUNK_TARGET = 1000


def clean(text: str) -> str:
    return TAG_PAT.sub("", text)


def is_header(line: str, max_len: int = 20) -> bool:
    s = line.strip()
    if not s or len(s) > max_len:
        return False
    return any(k in s for k in HEADER_KEYWORDS)


def split_sections(sentences: list[str]) -> list[tuple[str, list[str]]]:
    idx = [i for i, s in enumerate(sentences) if is_header(s)]
    if not idx:
        return [("(전체)", sentences)]
    bounds = idx + [len(sentences)]
    return [(sentences[a].strip(), sentences[a:b]) for a, b in zip(idx, bounds[1:])]


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

    total_docs = len(files)
    done_docs = 0
    skipped_docs = 0
    total_chunks = 0
    t_start = time.time()

    log(log_path, f"시작: 대상 문서 {total_docs}개 (이미 처리됨 {len(processed)}건은 건너뜀)")

    with open(out_path, "a", encoding="utf-8") as out_f:
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
                            "document_type": info.get("document_type"),
                            "decision_date": info.get("decision_date"),
                            "result": info.get("result"),
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
                        log_path,
                        f"진행 {done_docs}/{total_docs} (건너뜀 {skipped_docs}) "
                        f"| 누적 청크 {total_chunks} | 경과 {elapsed:.0f}s "
                        f"| 예상 잔여 {remaining:.0f}s",
                    )
            except Exception as e:
                log(log_path, f"오류 (doc_id={doc_id_probe}, file={fp}): {e!r}")

    log(log_path, f"완료: 문서 {done_docs}건 처리, {skipped_docs}건 건너뜀, 총 청크 {total_chunks}개")


if __name__ == "__main__":
    asyncio.run(main())
