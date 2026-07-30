# Client (Python)

역할: 텍스트 질의 CLI/UI
통신: API Server와 AsyncIO 기반 raw TCP 소켓 (Shared 프로토콜: shared/schemas/client-api)

## 구성 (네트워크 부분만 구현됨)
- `app/api_server_client.py` — `ApiServerClient`: API Server에 연결(`asyncio.open_connection`), 연결 시점에 `session_id`를 1회 생성해 이후 모든 질의에 재사용. 백그라운드 `_read_loop` 태스크가 커넥션을 계속 읽어서, 서버가 보내는 `{"type":"ping"}`에는 즉시 `{"type":"pong"}`으로 응답하고 나머지는 응답 큐에 넣는다 — 그래야 응답을 기다리는 동안뿐 아니라 사용자가 입력 중일 때도 ping에 응답할 수 있다. 커넥션이 끊기면 대기 중인 호출이 무한 대기하지 않고 `ConnectionError`를 던진다.
  - `send_query(rag_selector_query, question)`: **질문을 `CHUNK_SIZE`(20자)씩 잘라 small(1번)부터 big(N번)까지 순서대로 청크로 전송**한다. 첫 청크에만 `rag_selector_query`와 `final_request_number`(전체 청크 개수)를 실어 보내고, 매 청크에 `request_number`(현재 번호)와 `is_complete`(마지막 청크인지)를 담는다. 청크마다 응답을 기다리고, 마지막 청크의 응답(실제 결과)만 반환한다.
- `app/main.py` — 최소한의 실행 진입점: 연결 후 `input()`으로 질문 2개(Rag 선택 질문/실제 질문)를 받아 보내고 응답을 출력하는 것을 반복. `input()`은 `run_in_executor`로 별도 스레드에서 돌려 이벤트 루프가 막히지 않게 함(그래야 사용자가 입력하는 동안에도 백그라운드에서 ping에 응답 가능). 실제 대화형 UI(히스토리 표시, 예쁜 출력 등)는 범위 밖 — 순수 네트워크 동작 확인용.

## 환경변수
- `API_SERVER_HOST` (기본 `127.0.0.1`), `API_SERVER_PORT` (기본 `9000`)

## 실행
```bash
python3 -m app.main
```

## 검증 상태 (2026-07-30)
RagServer+DBServer+LLMServer+MainServer+API Server를 전부 띄운 실제 체인에 대해 이 `app/main.py`를 그대로 실행 — 같은 세션으로 질문 2개(판결문/법령)를 연속 전송해 둘 다 정상 응답 받았고, DB에 세션 1건+USER/BOT 메시지 4건이 정확히 쌓이는 것까지 확인 (테스트 데이터는 삭제함). 이것으로 6개 컴포넌트 전체가 실제로 연결되어 동작함을 확인.

ping/pong 추가 후: 45초 이상 아무 질의 없이 연결만 유지해도 백그라운드에서 pong을 계속 보내 연결이 끊기지 않음을 확인. 서로 다른 세션 2개가 동시에 느린 질의(수십 초)를 보내는 시나리오에서도 정상 완료·정상 종료됨을 확인 (API Server 쪽 쿼리 처리를 별도 태스크로 분리하는 수정과 함께 검증).

**청크 전송 검증(2026-07-30):** 49자짜리 질문을 20자씩 3개 청크로 나눠 보낸 e2e 테스트에서 DB에 재조립된 전체 질문이 정확히 저장됨을 확인. 서로 다른 세션 2개가 **같은 Rag**로 동시에 청크 전송해도 서로 안 섞이고 각자 정상 완료됨을 확인.

## 확정되지 않은 부분
- 실제 대화형 UI/UX (프롬프트 문구, 히스토리 표시, 에러 시 재연결 등)는 아직 없음 — 네트워크 계층만 구현됨
- 연결이 끊겼을 때 같은 session_id로 재연결하는 로직 없음
- 청크 크기(`CHUNK_SIZE=20`)는 임의로 정한 값 — 실제 운영에 맞는 크기는 미확정
