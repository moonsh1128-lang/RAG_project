# DBServer (C#)

역할: MySQL 기반 저장소
- 실제 테이블은 `/home/janghyeon/claude/rag-system/LawRagTableCreate.sql`로 이미 생성됨 (`chat_sessions`, `chat_messages`, `rag_retrieval_logs`)
- 토큰 저장은 이번 테이블 설계에서 제외 — 추후 별도 테이블/컬럼으로 추가 예정

통신:
- MainServer ↔ DBServer: HTTP REST (shared/schemas/main-db)
- DBServer ↔ AdminServer: HTTP REST (shared/schemas/db-admin) — 아직 미구현

## 엔드포인트
- `POST /sessions/ensure` — `chat_sessions` row가 없으면 생성 (있으면 no-op)
- `POST /messages` — `chat_messages` row 삽입, `message_id`는 서버가 GUID로 생성해 반환
- `POST /rag-logs` — `rag_retrieval_logs` row 삽입 (USER 메시지의 `message_id`에 연결), `log_id`는 서버가 GUID로 생성해 반환

## DB 접속
환경변수로 설정 (하드코딩 안 함): `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`. 하나라도 없으면 시작 시점에 바로 실패.

접속 정보(2026-07-30 확정): 호스트 `10.10.10.141`, 계정 `user1`, DB `LawLogeDataBase`. `user1`은 `chat_sessions`/`rag_retrieval_logs`에 ALL, `chat_messages`에는 SELECT/INSERT/UPDATE 권한(= DELETE 없음, 앱이 DELETE를 안 쓰므로 문제 없음).

(이전엔 `root`+`127.0.0.1`로 우회했음 — `root`는 `10.10.10.141` 호스트로 접속 시 MySQL 호스트 권한 문제로 `Access denied`가 났었는데, `user1`은 해당 호스트로 접속 가능하도록 권한이 설정되어 있음.)

## 실행 (검증 완료 — 2026-07-30, 실제 DB에 실제로 insert/select 확인)
```bash
DB_HOST=10.10.10.141 DB_USER=user1 DB_PASSWORD='...' DB_NAME=LawLogeDataBase dotnet run
```
`/sessions/ensure` → `/messages` → `/rag-logs` 순서로 호출해 실제 MySQL에 3개 테이블 모두 정상 삽입/조회됨을 확인 (테스트 데이터는 root 계정으로 삭제함 — `user1`은 `chat_messages` DELETE 권한이 없음).

MainServer + RagServer + DBServer를 동시에 띄워 `/query` 전체 흐름도 확인 — 세션 생성, USER 메시지 삽입, RagServer 호출(precedents 선택 + 검색), rag_retrieval_logs 삽입까지 전부 정상 동작하고 LLMServer 호출에서만 `Connection refused`로 실패 (LLMServer 미구현이라 예상된 동작).
