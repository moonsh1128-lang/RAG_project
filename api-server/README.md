# API Server (Python)

역할: Client 요청을 받아 MainServer로 전달하는 게이트웨이
통신:
- Client ↔ API Server: **AsyncIO 기반 raw TCP 소켓** (shared/schemas/client-api)
- API Server ↔ MainServer: HTTP REST (shared/schemas/api-main)

## 프로토콜 (Client ↔ API Server)
줄바꿈으로 구분된 JSON(NDJSON), 커넥션 하나 = 세션 하나. 커넥션을 유지한 채 여러 줄(질의)을 계속 보낼 수 있다 (Client가 대화 시작 시 만든 `session_id`를 계속 재사용하는 설계와 대응).

**2026-07-30부터 청크 단위 전송**: 질문 하나가 여러 줄(청크)로 나뉘어 온다. 첫 청크: `{"session_id":"...","rag_selector_query":"...","request_number":1,"final_request_number":N,"message_chunk":"...","is_complete":false}\n`. 이후 청크는 `rag_selector_query`/`final_request_number` 없이 `request_number`만 증가. 마지막 청크는 `is_complete:true`.

응답 한 줄: MainServer 응답을 그대로 전달 — 완성 전 청크는 `{"chunk_received": true, "request_number": N}`, 마지막 청크는 `{"result": "..."}` (또는 오류 시 `{"error": "..."}`)

API Server 자체는 `payload`를 그대로 MainServer에 릴레이할 뿐이라 **청크 프로토콜 도입에 따른 코드 변경이 없었다** — 필드를 들여다보지 않고 통째로 전달하는 설계 덕분.

## 구성
- `app/server.py` — `asyncio.start_server`로 TCP 서버를 열고, 커넥션마다 줄 단위로 읽어 MainServer에 전달, 응답을 다시 한 줄로 씀. JSON 파싱 실패나 MainServer 호출 실패는 커넥션을 끊지 않고 `{"error": ...}`로 응답. `sessions: dict[session_id, writer]` registry로 응답을 커넥션이 아니라 **session_id 기준**으로 찾아 전달함.
- `app/main_server_client.py` — MainServer `/query`에 대한 httpx 비동기 POST 래퍼

## 다중 클라이언트 / 세션 수명 관리
- **다중 클라이언트**: `asyncio.start_server`가 커넥션마다 독립된 `handle_client` 태스크를 돌리므로 기본적으로 동시 접속을 처리한다. 각 커넥션의 상태(`session_id`, ping 카운터)는 `ConnectionState` 인스턴스로 격리됨.
- **세션 부여/회수**: 커넥션에서 첫 질의가 오면 그 `session_id`를 `sessions` registry에 등록(부여)하고, 커넥션이 끊기면 `finally`에서 해당 `session_id`를 registry에서 제거(회수)한다.
- **ping/pong 하트비트**: 커넥션마다 `ping_loop` 태스크가 **10초 주기**로 `{"type": "ping"}`을 보낸다. 직전 ping에 pong이 안 왔으면 미수신 카운트를 올리고, **3회 연속 미수신 시 커넥션을 끊는다**.
- **쿼리 처리와 ping/pong 분리**: MainServer 호출(`process_query`)은 read loop와 별도 태스크로 실행한다 — 그렇지 않으면 LLM 생성처럼 오래 걸리는 쿼리 하나가 같은 커넥션의 read loop를 막아 그 사이 도착한 pong을 못 읽고, ping_loop가 "미수신"으로 착각해 정상 커넥션을 끊어버리는 문제가 있었음(실측: 두 클라이언트가 동시에 느린 질의를 보내자 재현됨). 태스크로 분리한 뒤에는 재현 안 됨.

## 환경변수
- `API_SERVER_HOST` (기본 `127.0.0.1`), `API_SERVER_PORT` (기본 `9000`)
- `MAIN_SERVER_URL` (기본 `http://localhost:8080`)

## 실행
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m app.server
```

## 검증 상태 (2026-07-30)
- MainServer 없이 단독 실행 → 접속 실패를 `{"error": "..."}`로 정상 응답함을 확인 (서버가 죽지 않음)
- RagServer+DBServer+LLMServer+MainServer를 모두 띄운 상태에서 실제 TCP 커넥션으로 두 번 연속 질의(같은 커넥션 = 같은 세션) → 둘 다 정상 응답, DB에 USER/BOT 메시지 4건과 `rag_retrieval_logs` 2건(각각 `precedents`/`statutes`)이 정확히 쌓이는 것까지 확인 (테스트 데이터는 삭제함)
- `127.0.0.1` 바인딩과 session_id 기반 registry 라우팅으로 바꾼 뒤에도 동일하게 정상 동작 확인
- **ping/pong**: pong을 안 보내는 raw 소켓 클라이언트로 실측 — 10s/20s/30s에 ping 수신, 40s 시점에 커넥션 종료(`EOF`) 확인. 반대로 Client의 실제 pong 응답 로직으로는 45초 넘게 연결 생존 확인.
- **다중 클라이언트 + 느린 질의**: 서로 다른 세션 2개를 동시에 접속시켜, 각각 25초 대기 후 LLM 응답이 오래 걸리는(수십 초) 질의를 동시에 보내는 시나리오로 재현 테스트 — 쿼리 처리를 별도 태스크로 분리하기 전에는 ping_loop가 오탐하여 커넥션을 끊었고(Client는 이 경우 무한 대기하는 버그도 있었음, 같이 수정), 분리 후에는 두 세션 모두 정상 완료·정상 종료됨을 확인

## 확정되지 않은 부분
- 연결이 끊겼다가 같은 세션으로 재접속하는 경우의 처리 (현재는 커넥션 생존 동안만 세션 유지, 재접속 시 새 커넥션에서 같은 session_id를 다시 보내면 DBServer의 `sessions/ensure`가 no-op이라 이어서 쓰는 것은 가능)
- 한 커넥션에 여러 쿼리를 응답 기다리지 않고 연달아 보내는(파이프라이닝) 경우 응답 순서가 뒤바뀔 수 있음 (현재 Client는 항상 응답을 기다린 뒤 다음 질의를 보내므로 실사용에는 영향 없음)
- 청크 전송 도중 커넥션이 끊기면 MainServer/RagServer에 남는 미완성 버퍼를 치우는 로직 없음 (해당 서버들의 README 참고)
