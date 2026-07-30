# RagServer (Python)

역할: 임베딩, 검색(RAG 판단) 처리
통신: MainServer ↔ RagServer, HTTP REST (shared/schemas/main-rag) — **청크 단위**로 주고받음
모델: 이 PC에 설치된 Ollama (`bge-m3` 임베딩)

## 청크 프로토콜 + RagChannel (`POST /rag`, 2026-07-30 도입)
MainServer는 질문을 여러 청크로 나눠 보낸다. 청크 하나: `{ SessionId, RagType(첫 청크만), RequestNumber, FinalRequestNumber(첫 청크만), MessageChunk, IsComplete }`.

1. `RequestNumber == 1`인 첫 청크가 오면 `RagType`으로 `select_rag()`를 실행해 이 세션이 쓸 Rag를 결정하고 `session_to_rag`에 기억한다.
2. 이 청크(와 이후 청크들)를 결정된 Rag 전용 `JsonMessageChannel`(**RagChannel**, `rag_channels[선택된_rag]`)에 넣는다. **Rag마다 채널이 따로 있어** 서로 다른 Rag를 쓰는 요청은 병렬로, 같은 Rag를 쓰는 요청은 그 채널 안에서 순서대로 처리된다.
3. 채널 핸들러(`handle_chunk`)는 `ChunkAssembly`(`chunk_assembly.py`)에 `session_id` 기준으로 청크를 쌓는다.
4. `IsComplete=true`이고 `1..FinalRequestNumber`까지 빠진 번호가 없으면 "완성"으로 보고 청크들을 합쳐 하나의 질문 텍스트로 만든 뒤, 실제 검색(`retrieve`)을 수행하고 소요시간(`RetrievalTimeMs`)도 잰다.
5. 완성 전 청크에는 `{ "IsFinal": false }`만 응답, 완성되면 `{ "IsFinal": true, SelectRag, message(재조립된 전체 질문), RagContext, RetrievalTimeMs }`를 응답한다.

서버 시작 시(`lifespan`) 이 PC의 Ollama에 `/api/tags`로 접속해 설치된 모델 목록을 읽어오고, 설정된 임베딩 모델(`bge-m3`)이 실제로 있는지 확인한다 — 없으면 시작 시점에 바로 실패한다 (`ollama_client.ensure_embed_model_available`).

## 실 데이터 연동 (2026-07-30)
`app/rag_sources.py`의 `REAL_DATA_FILES`가 가리키는 3개 JSONL(이미 bge-m3로 임베딩까지 끝난 청크 파일)을 서버 시작 시(`preload_real_data()`, `lifespan`) 한 번에 읽어 `VectorStore`에 올린다. 쿼리 임베딩만 그때그때 계산하고, 문서 임베딩은 파일에 있는 값을 그대로 쓴다(재임베딩 안 함).

| Rag | 파일 | 로드된 청크 수 | 비고 |
|---|---|---|---|
| precedents | `/home/janghyeon/claude/rag-system/RagFile/precedents_chunks.jsonl` | 5,985 | `casetype == "civil"`만 필터링(원본 6,169개 중 criminal/administration 제외) |
| interpretations | `/home/janghyeon/claude/rag-system/RagFile2/interpretations_chunks.jsonl` | 38 | 전체 |
| adjudications | `/home/janghyeon/claude/rag-system/RagFile3/adjudications_chunks.jsonl` | 2,422 | 전체 |
| statutes | (없음 — `mock_data.py` 가상 샘플로 대체) | - | 실 데이터 준비되면 `REAL_DATA_FILES`에 추가 |

파일은 서버 시작 시 한 번만 읽는다 — 실행 중 파일이 커져도(예: precedents가 다른 PC에서 계속 처리되는 중) 재시작 전엔 반영 안 됨(의도된 설계, 갱신 감지 불필요하다고 확정함).

## 가상 데이터 (`mock_data.py`)
statutes는 아직 실 데이터가 없어 짧은 가상 샘플 문장 몇 개를 그대로 쓴다. 전부 `[가상 샘플]`로 표시되어 있고 실제 법률 정보가 아니다.

`RAG_SOURCES`의 slug는 `precedents`/`statutes`/`adjudications`/`interpretations` — DBServer의 `rag_retrieval_logs.target_index` 컨벤션에 맞춘 것으로 확정됨.

## 실행
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 검증 상태 (2026-07-30 — 청크 프로토콜, 실제 체인)
- 질문 하나를 Client가 20자 단위로 3개 청크로 나눠 보낸 실제 e2e 테스트에서, DB의 `chat_messages.message_text`와 `rag_retrieval_logs.search_query` 둘 다 재조립된 전체 질문으로 정확히 저장됨을 확인 (즉 청크가 온전히 합쳐졌음)
- 서로 다른 세션 2개가 **같은 Rag 채널(precedents)**에 동시에 청크 전송 → 세션별로 정확히 분리되어 섞이지 않고 각자의 질문에 맞는 답이 나옴을 확인 (`ChunkAssembly`가 session_id로 격리되어 있어서)
- **실 데이터 검증**: 임대차보증금 반환(precedents), 근로시간 단축 임금보전(interpretations), 병원 기저귀 착용 인권침해(adjudications) 질의 각각 실제 관련 문서를 정확히 검색함을 확인. 전체 체인(Client→...→LLMServer)으로도 실제 판결 내용을 인용한 답변 생성까지 확인
- 서버 시작(preload) 소요시간: 5,985+38+2,422=8,445개 청크 로딩까지 포함해 수 초 이내

## 확정되지 않은 부분
- statutes 실 데이터가 준비되면 `REAL_DATA_FILES`에 추가 필요 (그 전까지는 `mock_data.py` 유지)
- precedents는 다른 PC에서 나머지 문서를 계속 처리 중 — 파일이 커진 걸 반영하려면 RagServer 재시작 필요(자동 갱신 감지는 하지 않기로 확정함)
- 청크 조립 도중 커넥션이 끊기거나 청크가 영영 안 오면 `session_to_rag`/`assemblies_by_rag`에 남은 상태를 치우는 타임아웃/정리 로직이 없음 (메모리 누수 가능성)
