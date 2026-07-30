# MainServer (C#)

역할: 오케스트레이션 허브 — RagServer/LLMServer/DBServer 호출
통신: 전부 HTTP REST (Controller 기반 ASP.NET Core)

## 구성
- `Models/` — 각 통신 구간의 DTO (`shared/schemas`와 대응, `JsonPropertyName`으로 필드명 고정)
- `Clients/` — 다운스트림 서버 typed `HttpClient` (RagServerClient, LlmServerClient, DbServerClient)
- `Services/ChunkAssembly.cs` — `ChunkAssemblyStore`: session_id별로 청크를 모아 완성된 질문 텍스트로 재조립 (DB 저장용)
- `Controllers/QueryController.cs` — `POST /query`: API Server가 호출하는 진입점

## 처리 흐름 (`POST /query`, 2026-07-30 청크 프로토콜로 수정)
API Server는 질문을 청크로 나눠 여러 번 호출한다. 청크 하나: `{ session_id, rag_selector_query(첫 청크만), request_number, final_request_number(첫 청크만), message_chunk, is_complete }`.

1. 청크가 오면 `ChunkAssemblyStore`에 `session_id` 기준으로 쌓는다 (MainServer 자신의 DB 저장용 재조립 — RagServer 판단과는 별개)
2. 이 청크를 **그대로** RagServer(`/rag`)에도 전달한다 — RagServer가 자체 RagChannel에서 재조립+완성 판단을 한다
3. RagServer 응답의 `IsFinal`이 `false`면, 아직 다 안 모인 것 — API Server에 `{ chunk_received: true, request_number }` ack만 돌려주고 끝
4. `IsFinal`이 `true`면(=RagServer가 전 청크를 모아 결정+검색까지 마쳤음) 그때부터 기존 파이프라인을 그대로 실행:
   - DBServer(`/sessions/ensure`)로 세션 보장
   - DBServer(`/messages`)에 USER 메시지(**MainServer가 재조립한 전체 질문**) 삽입 → `message_id`
   - DBServer(`/rag-logs`)에 검색 로그 저장 (`RagServer가 실측한 RetrievalTimeMs` 포함)
   - LLMServer(`/llm`) 호출 → `{ result }`
   - DBServer(`/messages`)에 BOT 메시지(`result`) 삽입
   - **LLMServer 응답을 그대로** API Server에 반환

## 다운스트림 주소 (환경변수)
- `RAG_SERVER_URL` (기본 `http://localhost:8001`)
- `LLM_SERVER_URL` (기본 `http://localhost:8002`)
- `DB_SERVER_URL` (기본 `http://localhost:8003`)

## 검증 상태 (2026-07-30)
- `dotnet build` 성공
- 실제 Client가 질문을 3개 청크로 나눠 보낸 e2e 테스트에서, `chat_messages`에 저장된 USER 메시지가 청크가 아니라 재조립된 전체 텍스트임을 확인
- 서로 다른 세션 2개가 동시에 청크 전송해도 각자 정상 완료됨을 확인

## 확정되지 않은 부분
- 클라이언트에게 최종적으로 어떤 응답을 돌려줄지 (현재는 LLM 결과를 그대로 반환)
- 청크 전송 도중 커넥션이 끊기면 `ChunkAssemblyStore`에 남은 미완성 항목을 치우는 로직 없음 (메모리 누수 가능성 — RagServer 쪽과 동일한 미해결 사항)
