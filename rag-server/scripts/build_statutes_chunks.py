"""
민사법 법령(statutes) 데이터 소스용 청크+임베딩 생성 스크립트.

판결문(precedents)과 다른 점: 문서 구조 자체가 조(제N조) 단위로 규칙적이라
섹션 감지나 오버사이즈 재분할이 필요 없음 — 조 1개 = 청크 1개.

사용법:
    .venv/bin/python scripts/build_statutes_chunks.py --source-dir "<법령 JSON 폴더>" --out "<출력 jsonl 경로>"
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
    "VL_01. 민사법_002. 법령_0001. 질의응답"
)

ARTICLE_PAT = re.compile(r"(제\d+조(?:의\d+)?)(\([^)]*\))")


def normalize_text(sentences) -> str:
    return sentences if isinstance(sentences, str) else "".join(sentences)


def split_articles(text: str) -> list[tuple[str, str, str]]:
    """반환: [(article_no, article_title, article_text), ...]"""
    matches = list(ARTICLE_PAT.finditer(text))
    if not matches:
        return [("(전체)", "", text)]
    articles = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        article_no = m.group(1)
        article_title = m.group(2).strip("()")
        articles.append((article_no, article_title, text[start:end].strip()))
    return articles


def load_processed_keys(out_path: str) -> set[str]:
    if not os.path.exists(out_path):
        return set()
    done = set()
    with open(out_path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                done.add(f"{rec['statute_name']}::{rec['article_no']}")
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
    processed = load_processed_keys(out_path)
    ollama = OllamaClient(args.ollama_url, args.embed_model)
    await ollama.ensure_embed_model_available()

    total_chunks = 0
    t_start = time.time()
    log(log_path, f"시작: 법령 파일 {len(files)}개 (이미 처리된 조문 {len(processed)}건은 건너뜀)")

    with open(out_path, "a", encoding="utf-8") as out_f:
        for fp in files:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            info = data.get("info", {})
            statute_name = info.get("statute_name") or os.path.basename(fp)
            text = normalize_text(data.get("taskinfo", {}).get("sentences", ""))
            articles = split_articles(text)

            doc_chunks = 0
            for article_no, article_title, article_text in articles:
                key = f"{statute_name}::{article_no}"
                if key in processed:
                    continue
                if not article_text.strip():
                    continue
                embedding = await ollama.embed(article_text)
                record = {
                    "text": article_text,
                    "embedding": embedding,
                    "statute_name": statute_name,
                    "statute_abbrv": info.get("statute_abbrv"),
                    "statute_type": info.get("statute_type"),
                    "statute_category": info.get("statute_category"),
                    "effective_date": info.get("effective_date"),
                    "proclamation_date": info.get("proclamation_date"),
                    "article_no": article_no,
                    "article_title": article_title,
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()
                doc_chunks += 1
                total_chunks += 1

            elapsed = time.time() - t_start
            log(log_path, f"완료: {statute_name} ({doc_chunks}개 조문 임베딩) | 누적 {total_chunks} | 경과 {elapsed:.0f}s")

    log(log_path, f"전체 완료: 총 {total_chunks}개 조문 청크 생성")


if __name__ == "__main__":
    asyncio.run(main())
