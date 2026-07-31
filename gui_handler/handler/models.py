"""
DB 테이블 구조를 반영한 화면단(ViewModel/View)용 데이터 모델.

- chat_sessions, chat_messages: 2026-07-30 실제 DB 스키마(MySQL Workbench) 확인 후 반영.
- rag_retrieval_logs: 아직 실제 테이블 컬럼을 직접 확인하지 못해, 이전 문서(PROGRESS.md/
  RawRagProject.md) 설명 기반으로 추정한 상태. 실제 스키마 확인되면 다시 맞춰야 함.

실제 Handler가 어떤 형태로 값을 반환하든, "Handler 반환값 -> 이 모델로 변환"하는
어댑터 한 곳만 나중에 손보면 되도록, 화면이 원하는 형태를 여기서 먼저 확정해둔다.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SenderType(str, Enum):
    USER = "USER"
    BOT = "BOT"


@dataclass
class ChatSession:
    """chat_sessions 테이블 컬럼 + 화면용 preview(테이블 컬럼 아님)."""
    session_id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    # 사이드바 미리보기 문구. title이 비어있는 경우가 많아(현재 서버가 안 채움),
    # get_latest_message()로 가져온 "마지막 메시지" 텍스트를 여기 채운다.
    preview: Optional[str] = None


@dataclass
class RagRetrievalLog:
    """
    rag_retrieval_logs 컬럼 추정치 (실제 스키마 미확인 - 확인되면 수정 필요).
    """
    log_id: str
    message_id: str
    search_query: str
    target_index: str  # precedents / statutes / adjudications / interpretations
    top_k: int
    retrieved_chunks: list[str] = field(default_factory=list)
    retrieval_time_ms: Optional[int] = None


@dataclass
class ChatMessage:
    """chat_messages 테이블 컬럼 그대로."""
    message_id: str
    session_id: str
    sender_type: SenderType
    message_text: str
    created_at: datetime
    rag_log: Optional[RagRetrievalLog] = None  # BOT 메시지일 때만 채워짐 (테이블 컬럼 아님, 조인 결과)