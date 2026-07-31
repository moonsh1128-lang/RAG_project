# Client ↔ API Server ↔ MainServer API 변경사항

`bb812e7`(고소장 기능) 이후 세션에서 있었던 변경 3가지를 정리한다. 최신 스키마는
[shared/schemas/client-api/](shared/schemas/client-api/), [shared/schemas/api-main/](shared/schemas/api-main/) 참고.

## 1. 청킹 책임을 Client → API Server로 이관

**이전**: Client가 질문을 20자 단위로 잘라 청크마다 API Server에 전송하고, 매번 응답(ack 또는 최종 결과)을
기다린 뒤 다음 청크를 보냈다. Client-API 구간 자체가 청크 프로토콜이었다.

**이후**: Client는 질문 전체를 한 번에 보낸다. 청킹은 API Server([main_server_client.py](api-server/app/main_server_client.py))가
MainServer를 호출할 때 내부적으로 수행한다 — MainServer/RagServer 쪽 청크 프로토콜(20자 단위, `request_number`/`is_complete` 등)은 전혀 안 바뀜.

```diff
- Client -> API Server: 청크 1, 청크 2, ... (각각 왕복)
+ Client -> API Server: 질문 전체 (왕복 1번)
  API Server -> MainServer: 청크 1, 청크 2, ... (기존과 동일, 여기로 옮겨감)
```

Client-API 구간의 질문 메시지 형태:
```diff
  {
    "session_id": "...",
    "rag_selector_query": "...",
-   "request_number": 1,
-   "final_request_number": 3,
-   "message_chunk": "...",
-   "is_complete": false
+   "question": "실제 질문 전체"
  }
```

이 변화로 Client는 더 이상 청크 ack(`chunk_received`)를 받지 않는다 — 질문 하나에 응답 하나.

## 2. 후속 질문 재작성(rewrite)을 위한 `message_count`/`history` 추가

Client가 세션 동안 메모리에 들고 있는 이전 질문/답변을 매 질의마다 함께 보내도록 필드 2개 추가.

```json
{
  "session_id": "...",
  "rag_selector_query": "...",
  "question": "그럼 소송을 제기하면 보통 얼마나 걸리나요",
  "message_count": 2,
  "history": [
    { "question": "임대차 계약이 끝났는데...", "answer": "임대차 계약이 끝난 후..." }
  ]
}
```

- `message_count == 1`: 기존 로직 그대로(재작성 없음)
- `message_count >= 2`: MainServer가 `history` + 새 질문을 LlmServer의 `/llm/rewrite`(신규 엔드포인트)에 보내
  독립적인 질문으로 재작성 → **LLM 답변 생성 단계에서만** 재작성된 질문을 사용(RagServer 검색은 원문 그대로)

API Server([main_server_client.py](api-server/app/main_server_client.py))는 이 두 필드를 첫 번째 청크(`request_number == 1`)에만 실어 MainServer로 전달한다.

## 3. 고소장(`type: "complaint"`) 요청 필드 축소

증거자료(`evidence`)/제출처(`submission_target`) 필드를 요청에서 제거했다 — 서식 자체에서
[증거물]/날짜/서명/제출처 섹션을 뺐기 때문(생성 결과가 고소취지/고소사실까지만 나오도록 변경).

```diff
  {
    "type": "complaint",
    "session_id": "...",
    "complainant_name": "...",
    "complainant_representative": "...",
    "complainant_address": "...",
    "accused_name": "...",
    "accused_address": "...",
    "charge": "...",
-   "incident_description": "...",
-   "evidence": ["...", "..."],
-   "submission_target": "..."
+   "incident_description": "..."
  }
```

## 최종 형태 요약 (Client → API Server)

| 메시지 | 필드 |
|---|---|
| 질문 | `session_id`, `rag_selector_query`, `question`, `message_count`, `history` |
| 고소장 생성 (`type: "complaint"`) | `session_id`, `complainant_name`, `complainant_representative`, `complainant_address`, `accused_name`, `accused_address`, `charge`, `incident_description` |
| 하트비트 응답 (`type: "pong"`) | (없음) |
