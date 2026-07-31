"""
실제 팀원 Handler가 나오기 전까지 쓰는 더미 구현.
ViewModel/View 개발은 이걸로 먼저 진행하고, 실제 Handler가 오면
이 클래스가 있던 자리에 어댑터 클래스로 교체한다 (인터페이스는 동일하게 유지).
"""
import uuid
from datetime import datetime, timedelta

from handler.handler_interface import DbHandlerInterface
from handler.models import ChatSession, ChatMessage, SenderType, RagRetrievalLog


class MockDbHandler(DbHandlerInterface):
    def __init__(self):
        self._sessions, self._messages = self._build_dummy_data()

    def get_sessions(self) -> list[ChatSession]:
        return list(self._sessions)

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        return [m for m in self._messages if m.session_id == session_id]

    def _build_dummy_data(self):
        now = datetime.now()
        user_id = str(uuid.uuid4())
        session_ids = [str(uuid.uuid4()) for _ in range(3)]

        sessions = [
            ChatSession(
                session_id=session_ids[0],
                user_id=user_id,
                title=None,
                created_at=now - timedelta(days=2),
                updated_at=now - timedelta(days=2) + timedelta(hours=1),
                preview="[더미 응답] 상속 개시를 안 날로부터 3개월 이내입니다. (mock 데이터)",
            ),
            ChatSession(
                session_id=session_ids[1],
                user_id=user_id,
                title=None,
                created_at=now - timedelta(days=1),
                updated_at=now - timedelta(days=1) + timedelta(hours=1),
                preview="[더미 응답] 임대인 실거주 등 정당한 사유가 있으면 가능합니다. (mock 데이터)",
            ),
            ChatSession(
                session_id=session_ids[2],
                user_id=user_id,
                title="손해배상 청구권 소멸시효는?",
                created_at=now,
                updated_at=now,
            ),
        ]

        messages = [
            ChatMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_ids[0],
                sender_type=SenderType.USER,
                message_text="상속 포기 신고 기한이 어떻게 되나요?",
                created_at=now - timedelta(days=2),
            ),
            ChatMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_ids[0],
                sender_type=SenderType.BOT,
                message_text="[더미 응답] 상속 개시를 안 날로부터 3개월 이내입니다. (mock 데이터)",
                created_at=now - timedelta(days=2) + timedelta(hours=1),
                rag_log=RagRetrievalLog(
                    log_id=str(uuid.uuid4()),
                    message_id=str(uuid.uuid4()),
                    search_query="상속 포기 신고 기한",
                    target_index="statutes",
                    top_k=1,
                    retrieved_chunks=["[가상 샘플] 민법 제1019조 ..."],
                    retrieval_time_ms=1200,
                ),
            ),
            ChatMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_ids[1],
                sender_type=SenderType.USER,
                message_text="임대차 계약 갱신 거절 사유가 궁금해요",
                created_at=now - timedelta(days=1),
            ),
            ChatMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_ids[1],
                sender_type=SenderType.BOT,
                message_text="[더미 응답] 임대인 실거주 등 정당한 사유가 있으면 가능합니다. (mock 데이터)",
                created_at=now - timedelta(days=1) + timedelta(hours=1),
                rag_log=RagRetrievalLog(
                    log_id=str(uuid.uuid4()),
                    message_id=str(uuid.uuid4()),
                    search_query="임대차 계약 갱신 거절 사유",
                    target_index="precedents",
                    top_k=1,
                    retrieved_chunks=["[가상 샘플] 대법원 판례 ..."],
                    retrieval_time_ms=980,
                ),
            ),
        ]

        return sessions, messages