"""
팀원이 만든 DBHandler(handler/db_handler.py, pymysql 직접 사용)를
DbHandlerInterface 규격에 맞춰주는 어댑터.

DBHandler의 리턴값은 raw dict(DictCursor 결과)라서, 여기서 ChatSession/ChatMessage/
RagRetrievalLog dataclass로 변환한다.

GUI가 로그인 없이 실행되므로 세션 목록은 전체 조회(get_all_sessions)를 쓴다.
"""
import json
from typing import Optional

from handler.db_handler import DBHandler
from handler.handler_interface import DbHandlerInterface
from handler.models import ChatMessage, ChatSession, RagRetrievalLog, SenderType


class RealDbHandler(DbHandlerInterface):
    def get_sessions(self) -> list[ChatSession]:
        with DBHandler() as h:
            rows = h.get_all_sessions()
            sessions = [self._to_session(r) for r in rows]
            for session in sessions:
                latest = h.get_latest_message(session.session_id)
                if latest is not None:
                    session.preview = self._truncate(latest["message_text"])
        return sessions

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        with DBHandler() as h:
            rows = h.get_conversation_with_logs(session_id)
        return self._rows_to_messages(rows)

    # ---------------- 변환 ----------------
    @staticmethod
    def _to_session(row: dict) -> ChatSession:
        return ChatSession(
            session_id=row["session_id"],
            user_id=row["user_id"],
            title=row.get("title"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _truncate(text: str, max_len: int = 40) -> str:
        text = text.strip().replace("\n", " ")
        return text if len(text) <= max_len else text[:max_len] + "..."

    @staticmethod
    def _parse_retrieved_chunks(value) -> list[str]:
        """retrieved_chunks 컬럼이 JSON 문자열/JSON 타입/None 무엇으로 오든 list[str]로 정규화."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [str(parsed)]
        except (TypeError, ValueError):
            return [str(value)]

    @classmethod
    def _rows_to_messages(cls, rows) -> list[ChatMessage]:
        """
        get_conversation_with_logs()는 메시지 x 로그로 LEFT JOIN된 결과라서,
        같은 message_id가 여러 행으로 나올 수 있다(로그가 여러 건인 경우).
        message_id 기준으로 묶어 ChatMessage 하나당 RagRetrievalLog 하나로 정리한다.
        (지금 파이프라인상 메시지당 로그는 최대 1건이라, 여러 건이면 첫 번째만 사용)
        """
        messages: dict[str, ChatMessage] = {}
        order: list[str] = []

        for row in rows:
            message_id = row["message_id"]
            if message_id not in messages:
                order.append(message_id)
                messages[message_id] = ChatMessage(
                    message_id=message_id,
                    session_id=row["session_id"],
                    sender_type=SenderType(row["sender_type"]),
                    message_text=row["message_text"],
                    created_at=row["created_at"],
                    rag_log=None,
                )

            if row.get("log_id") is not None and messages[message_id].rag_log is None:
                messages[message_id].rag_log = RagRetrievalLog(
                    log_id=row["log_id"],
                    message_id=message_id,
                    search_query=row["search_query"],
                    target_index=row["target_index"],
                    top_k=row["top_k"],
                    retrieved_chunks=cls._parse_retrieved_chunks(row.get("retrieved_chunks")),
                    retrieval_time_ms=row.get("retrieval_time_ms"),
                )

        return [messages[mid] for mid in order]