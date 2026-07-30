# LLMServer (C#)

역할: Ollama를 감싸는 래퍼 서버 (직접 구현)
통신: MainServer ↔ LLMServer, HTTP REST (shared/schemas/main-llm)
모델: 이 PC에 설치된 Ollama (`llama3.2:3b` 생성)

## 구성
- `Clients/OllamaClient.cs` — Ollama `/api/tags`(모델 목록), `/api/chat` 호출
- `Controllers/LlmController.cs` — `POST /llm`: `{ retrieved_content, question }`을 받아 `[참고 정보]`/`[질문]` 형태 프롬프트로 감싸 Ollama에 전달, `{ result }` 응답
- `Program.cs`: 서버 시작 시 이 PC의 Ollama에서 생성 모델(`llama3.2:3b`)이 실제로 있는지 확인, 없으면 시작 시점에 바로 실패

## 환경변수
- `OLLAMA_HOST` (기본 `http://localhost:11434`)
- `OLLAMA_CHAT_MODEL` (기본 `llama3.2:3b`)

## 검증 상태 (2026-07-29 — 이 PC의 Ollama로 실제 확인)
단독 호출과 RagServer+DBServer+MainServer 전체 체인 양쪽으로 실제 생성 결과 확인. 처음 프롬프트("참고 정보만 근거로, 없으면 모른다고 말해라")는 llama3.2:3b가 관련 내용이 있는데도 답변을 거부하는 경우가 있어, "참고 정보를 근거로 질문에 직접 답하라"는 더 직접적인 지시로 바꿔 해결함.

주의: 3B급 소형 모델이라 답변에 원문에 없는 예시를 지어내거나(예: 없는 조문 번호, 구체적 금액), 드물게 다른 언어 문자가 섞여 나오는 등 품질이 완벽하지 않음 — 실 데이터/실 사용 전에 프롬프트나 모델 자체를 더 다듬을 필요가 있음.

## 확정되지 않은 부분
- 프롬프트 문구는 초안 수준 — 실제 법률 답변 품질 기준으로 다시 다듬을 필요
- 3B 모델의 사실 관계 왜곡(hallucination) 대응 방안
