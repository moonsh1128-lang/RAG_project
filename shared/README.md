# Shared

서버 간 요청/응답 계약을 JSON Schema로 정의한다.
각 하위 폴더는 통신 구간 하나에 대응하며, 아직 필드는 확정되지 않아 스켈레톤만 존재한다.

- client-api: Client ↔ API Server (AsyncIO)
- api-main: API Server ↔ MainServer (HTTP REST)
- main-rag: MainServer ↔ RagServer (HTTP REST)
- main-llm: MainServer ↔ LLMServer (HTTP REST)
- main-db: MainServer ↔ DBServer (HTTP REST)
- db-admin: DBServer ↔ AdminServer (HTTP REST)
