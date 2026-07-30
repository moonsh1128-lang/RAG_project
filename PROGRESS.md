# RAG 시스템 제작 완료 현황

> 2026-07-30 기준. 확정 사항/미확정 항목의 전체 목록은 [`RawRagProject.md`](../RawRagProject.md) 참고. 이 문서는 지금까지 **만든 것**을 파트별로 정리한다.

## 전체 구조
```
Client ──(AsyncIO/NDJSON)── API Server ──(HTTP REST)── MainServer
                                                      ├──(HTTP REST)── RagServer
                                                      ├──(HTTP REST)── LLMServer
                                                      └──(HTTP REST)── DBServer
```
6개 컴포넌트(AdminServer는 DBServer와 역할 중복으로 폐기) 전부 구현 완료, 실제 Ollama·MySQL로 전체 체인 end-to-end 검증 완료.

---

## Client (`client/`, Python)
- `app/api_server_client.py`: `ApiServerClient` — API Server 접속 시 `session_id`를 1회 생성해 이후 모든 질의에 재사용. 백그라운드 태스크가 서버의 `ping`에 즉시 `pong`으로 응답하고, 연결이 끊기면 대기 중인 호출이 무한 대기 대신 `ConnectionError`를 던짐
  - `send_query()`: 질문을 `CHUNK_SIZE`(20자)씩 잘라 순서대로(청크 번호 1..N) 전송, 마지막 청크의 응답(실제 결과)만 반환
- `app/main.py`: 최소 실행 진입점(`input()` 기반 반복 질의, `run_in_executor`로 이벤트 루프는 안 막음) — 네트워크 계층만 구현, 대화형 UI/UX는 미구현
- 검증: 실제 전체 체인에 대해 이 스크립트를 그대로 실행해 같은 세션으로 질의 2회 연속 → 정상 응답 + DB 반영 확인. 45초 이상 유휴 상태로도 연결 유지 확인.

## API Server (`api-server/`, Python)
- `app/server.py`: `asyncio.start_server` 기반 TCP 서버. **줄바꿈 구분 JSON(NDJSON), 커넥션 하나 = 세션 하나** 프로토콜. `session_id → writer` registry로 MainServer 응답을 session_id 기준으로 해당 Client에 전달. JSON 파싱/MainServer 호출 실패 시에도 커넥션을 끊지 않고 `{"error": ...}` 응답
- **다중 클라이언트**: 커넥션마다 독립 태스크(`asyncio.start_server` 기본 동작) + 커넥션별 `ConnectionState`
- **ping/pong 하트비트**: 10초 주기 ping, 3회 연속 미수신 시 커넥션 종료. MainServer 호출(`process_query`)을 read loop와 별도 태스크로 분리해, 느린 쿼리가 ping/pong 처리를 막아 오탐 종료되는 버그를 해결
- `app/main_server_client.py`: MainServer `/query` httpx 비동기 호출
- 환경변수: `API_SERVER_HOST`(`127.0.0.1`)/`API_SERVER_PORT`(`9000`), `MAIN_SERVER_URL`
- 검증: 단독 실행 시 오류 응답 확인, 전체 체인에서 세션당 연속 질의 정상 동작 확인, ping/pong 타임아웃(40초 종료)·정상 pong 생존·동시 느린 질의 2세션 모두 실측 확인

## MainServer (`main-server/`, C#, ASP.NET Core Controller)
- `Controllers/QueryController.cs` (`POST /query`): 청크 하나를 받아 처리
  1. `Services/ChunkAssembly.cs`의 `ChunkAssemblyStore`(session_id별)에 청크 축적 — DB 저장용 전체 질문 재조립
  2. 이 청크를 그대로 RagServer(`/rag`)에도 전달
  3. RagServer 응답이 `IsFinal:false`면 API Server에 `chunk_received` ack만 반환
  4. `IsFinal:true`(RagServer가 전 청크 모아 결정+검색까지 완료)면 그때 세션 보장 → USER 메시지(재조립 전체 텍스트) 삽입 → 검색 로그 삽입 → LLMServer 호출 → BOT 메시지 삽입 → LLM 응답을 가공 없이 반환
- `Clients/`: `RagServerClient`/`LlmServerClient`/`DbServerClient` (typed `HttpClient`)
- `Models/`: 각 구간 DTO, `JsonPropertyName`으로 wire 필드명 고정 (RagServer 쪽은 `RagType`/`SelectRag` 등 원래 대소문자 유지)
- 다운스트림 주소는 환경변수(`RAG_SERVER_URL`/`LLM_SERVER_URL`/`DB_SERVER_URL`)
- 검증: `dotnet build` 성공, 3개 청크로 나뉜 질문이 DB에 재조립된 전체 텍스트로 저장됨을 확인

## RagServer (`rag-server/`, Python, FastAPI)
- `app/channel.py`: `JsonMessageChannel` — 동시 요청도 들어온 순서대로 순차 처리하는 큐. **Rag 4개마다 하나씩(RagChannel)** 인스턴스화해, 같은 Rag끼리는 순서대로·다른 Rag끼리는 병렬로 처리
- `app/chunk_assembly.py`: `ChunkAssembly` — session_id 기준으로 청크를 모아 완성(빠진 번호 없음 + `IsComplete`) 여부 판단, 재조립
- `app/ollama_client.py`: 이 PC의 Ollama `/api/embed` 호출 + 시작 시 `/api/tags`로 임베딩 모델 존재 확인
- `app/rag_selector.py`: 4개 Rag 소스 설명과의 코사인 유사도로 결정. slug는 `precedents`/`statutes`/`adjudications`/`interpretations` (DBServer의 `target_index` 컨벤션에 맞춤)
- `app/vector_store.py` + `app/mock_data.py`: 실 데이터 없어 가상 샘플 문장으로 코사인 검색 (전부 `[가상 샘플]` 표시)
- `app/main.py` (`POST /rag`): 1번 청크의 `RagType`으로 `decide()` 후 해당 RagChannel에 청크 제출, 완성되면 검색+소요시간(`RetrievalTimeMs`) 측정 후 `{IsFinal:true, ...}` 응답, 아니면 `{IsFinal:false}`
- 검증: 4개 Rag 각각 올바른 선택+검색 확인, 동시요청 4개 처리 확인, 청크 재조립 e2e 확인, 같은 Rag 채널에 다른 세션 2개 동시 전송해도 안 섞임 확인

## LLMServer (`llm-server/`, C#, ASP.NET Core Controller)
- `Clients/OllamaClient.cs`: 시작 시 생성 모델(`llama3.2:3b`) 존재 확인, `/api/chat` 호출(temperature 0)
- `Controllers/LlmController.cs` (`POST /llm`): `[참고 정보]`/`[질문]` 프롬프트로 감싸 Ollama에 전달
- 검증: 실제 생성 결과 확인. 초기 프롬프트가 llama3.2:3b의 답변 거부를 유발해 더 직접적인 지시로 수정함 (3B 모델 특유의 hallucination은 남아있음 — 사실무근 조문/금액을 지어내거나 드물게 다른 언어 혼입)

## DBServer (`db-server/`, C#, ASP.NET Core Controller + MySqlConnector)
- 실제 MySQL(`LawLogeDataBase`, 테이블은 사용자가 `LawRagTableCreate.sql`로 이미 생성)에 연결
- `POST /sessions/ensure`(no-op upsert), `POST /messages`(GUID 생성), `POST /rag-logs`(GUID 생성)
- `Data/LawLogRepository.cs`: 파라미터화된 SQL로 3개 테이블(`chat_sessions`/`chat_messages`/`rag_retrieval_logs`) 직접 insert
- 접속 정보는 `DB_HOST`/`DB_USER`/`DB_PASSWORD`/`DB_NAME` 환경변수 필수(하드코딩 없음). 호스트 `10.10.10.141`, 계정 `user1` (초기엔 `root`가 이 호스트로 접속 거부되어 `127.0.0.1`로 우회했다가, `user1` 권한 설정 후 원래 주소로 확정)
- 검증: 3개 엔드포인트 모두 실제 DB insert/select 확인

## Shared 프로토콜 (`shared/schemas/`)
서버 간 요청/응답 계약을 JSON Schema로 정의. 구간: `client-api`, `api-main`, `main-rag`, `main-llm`, `main-db`(`session-ensure`/`message`/`rag-log`).

---

## End-to-end 검증 이력
1. RagServer 단독 (Ollama 실연동, 가상 데이터)
2. MainServer + RagServer
3. DBServer 단독 (실제 MySQL insert/select)
4. MainServer + RagServer + DBServer
5. + LLMServer (4개 서버 동시 기동, 전체 흐름 첫 성공)
6. + API Server (실제 TCP 소켓, 세션 재사용 확인)
7. + Client (실제 실행 스크립트로 최종 확인)
8. 응답 전달 경로(session_id 기반)/localhost 바인딩/검색 소요시간 실측 반영 후 재검증
9. ping/pong 하트비트 + 다중 클라이언트 세션 관리 추가, 동시 느린 질의 2세션 시나리오로 오탐 종료 버그 발견·수정 후 재검증
10. 청크 전송 프로토콜 전면 도입(수정 전 전체 백업 후 진행) — Client→API→MainServer→RagServer 4단 릴레이, RagServer의 Rag별 채널에서 최종 재조립+검색. 단일 세션 3청크 재조립 확인 + 같은 Rag 채널에 다른 세션 2개 동시 전송해도 안 섞임을 확인

매 단계 테스트 데이터는 삭제하고 진행함.

## 남은 것
데이터 소스 파일 확보, Client 실제 UI/UX, LLM 프롬프트/hallucination 대응, 검색 파라미터(top-K 등) 확정, client-api/api-main 응답 스키마 등 — 전체 목록은 [`RawRagProject.md`](../RawRagProject.md)의 "미확정" 섹션 참고.
