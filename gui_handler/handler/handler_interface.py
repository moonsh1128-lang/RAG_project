"""
DB 조회 Handler의 추상 인터페이스.

팀원이 실제 Handler를 어떤 형태(위치/시그니처)로 만들든, ViewModel은
이 인터페이스에만 의존한다. 실제 Handler가 나오면:

  - Handler가 Client 안에서 돈다면 -> 이 인터페이스를 구현하는 어댑터 클래스만 새로 작성
  - Handler가 서버 사이드(DBServer 등)라면 -> 이 인터페이스를 구현하면서 내부에서
    네트워크 호출(API Server 경유)을 하는 어댑터 클래스를 작성

두 경우 모두 ViewModel/View 코드는 손댈 필요가 없다.
"""
from abc import ABC, abstractmethod

from handler.models import ChatSession, ChatMessage


class DbHandlerInterface(ABC):
    @abstractmethod
    def get_sessions(self) -> list[ChatSession]:
        """세션 목록 조회 (최근 순)."""
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, session_id: str) -> list[ChatMessage]:
        """특정 세션의 메시지 히스토리 조회 (시간 순)."""
        raise NotImplementedError