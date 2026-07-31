"""
PySide6 기반 ViewModel.

두 가지를 조합한다:
- DbHandlerInterface: 지난 세션 목록/히스토리 조회 (지금은 Mock)
- QueryClient: 지금 이 창에서 진행 중인 대화의 실시간 전송/수신 (API Server 실연동)

View는 이 클래스의 Signal만 구독한다.
"""
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from handler.handler_interface import DbHandlerInterface
from handler.models import ChatSession, ChatMessage, SenderType
from gui.network_client import QueryClient


class ChatViewModel(QObject):
    # 과거 세션 조회 (Handler)
    sessionsChanged = Signal(list)        # list[ChatSession]
    messagesChanged = Signal(list)        # list[ChatMessage] - 과거 세션을 선택했을 때 히스토리 전체 갱신
    currentSessionChanged = Signal(str)   # session_id
    errorOccurred = Signal(str)

    # 지금 이 창에서 진행 중인 실시간 대화 (QueryClient)
    domainMessageAdded = Signal(str)      # 1단계: 사용자가 입력한 "상담 분야" 텍스트
    userMessageAdded = Signal(str)        # 2단계: 사용자가 입력한 "상황" 텍스트 (전송 즉시)
    botMessageAdded = Signal(str)         # 서버로부터 받은 최종 답변 텍스트
    connectionStatusChanged = Signal(str) # "connecting" / "connected" / "failed"
    chatReset = Signal()                  # "새 채팅" 시작 - View는 채팅 영역을 비워야 함
    inputPromptChanged = Signal(str)      # 입력창 placeholder 텍스트 (1단계/2단계 전환용)

    # 고소장 생성 - 기존 채팅 흐름과는 완전히 별개 (DB 미사용, RAG 미사용)
    documentGenerated = Signal(str)
    complaintFailed = Signal(str)

    DOMAIN_PROMPT = "상담 분야를 자유롭게 설명해 주세요 (예: 임대차, 상속, 손해배상 등)..."
    SITUATION_PROMPT = "상황을 육하원칙에 따라 설명해 주세요..."

    def __init__(self, handler: DbHandlerInterface, query_client: QueryClient, parent=None):
        super().__init__(parent)
        self._handler = handler
        self._query_client: Optional[QueryClient] = None
        self._sessions: list[ChatSession] = []
        self._messages: list[ChatMessage] = []
        self._current_session_id: Optional[str] = None
        self._pending_domain: Optional[str] = None  # 1단계 입력을 2단계 전송 전까지 들고 있음

        self._wire_query_client(query_client)

    def _wire_query_client(self, query_client: QueryClient) -> None:
        self._query_client = query_client
        query_client.connected.connect(lambda: self.connectionStatusChanged.emit("connected"))
        query_client.connectFailed.connect(self._on_connect_failed)
        query_client.responseReceived.connect(self.botMessageAdded)
        query_client.errorOccurred.connect(self.errorOccurred)
        query_client.documentGenerated.connect(self.documentGenerated)
        query_client.complaintFailed.connect(self.complaintFailed)

    @Slot(dict)
    def submit_complaint(self, fields: dict):
        """
        고소장 생성 요청. 기존 채팅용 커넥션(self._query_client)을 그대로 재사용한다 -
        session_id는 서버가 아예 안 쓰므로(DbServer 호출 없음) 어떤 세션에 붙어있든 상관없다.
        """
        self._query_client.send_complaint(fields)

    # ---- 실시간 대화 (지금 창의 새 질의) ----
    @Slot()
    def start_connection(self):
        self.connectionStatusChanged.emit("connecting")
        self._query_client.connect_to_server()

    def _on_connect_failed(self, message: str):
        self.connectionStatusChanged.emit("failed")
        self.errorOccurred.emit(message)

    @Slot(str)
    def send_message(self, text: str):
        """
        입력창 하나를 2단계로 나눠 받는다.
        1단계(분야 미확정 상태): 이번 입력을 rag_selector_query 후보로 저장만 하고 전송 안 함.
        2단계(분야 확정된 상태): 이번 입력을 question으로 써서 실제 전송.
        """
        text = text.strip()
        if not text:
            return

        if self._pending_domain is None:
            self._pending_domain = text
            self.domainMessageAdded.emit(text)
            self.inputPromptChanged.emit(self.SITUATION_PROMPT)
            return

        rag_selector_query = self._pending_domain
        question = text
        self._pending_domain = None

        self.userMessageAdded.emit(question)
        self.inputPromptChanged.emit(self.DOMAIN_PROMPT)
        self._query_client.send(rag_selector_query, question)

    @Slot()
    def start_new_chat(self):
        """
        새 채팅 시작 - 기존 커넥션(옛 session_id)을 닫고 새 QueryClient(새 session_id)로 교체한다.
        ApiServerClient는 커넥션 하나 = 세션 하나 구조라, "새 대화"는 곧 새 커넥션을 뜻한다.
        """
        old_client = self._query_client
        if old_client is not None:
            old_client.close()

        self._wire_query_client(QueryClient())
        self._current_session_id = None
        self._pending_domain = None
        self.chatReset.emit()
        self.inputPromptChanged.emit(self.DOMAIN_PROMPT)
        self.start_connection()

    # ---- 과거 세션 조회 (Handler / Mock) ----
    @Slot()
    def load_sessions(self):
        try:
            self._sessions = self._handler.get_sessions()
            self.sessionsChanged.emit(self._sessions)
        except Exception as e:
            self.errorOccurred.emit(f"세션 목록 조회 실패: {e}")

    @staticmethod
    def _build_history_pairs(messages: list[ChatMessage]) -> list[dict]:
        """
        USER 메시지 다음에 바로 BOT 메시지가 오는 것만 완결된 한 턴으로 묶는다.
        (마지막이 아직 답변 안 달린 USER 메시지로 끝나는 경우는 미완결 턴이라 제외 -
        message_count도 완결된 턴 수만 세야 서버의 rewrite 판단(message_count>=2)과 맞는다.)
        """
        pairs = []
        i = 0
        while i < len(messages) - 1:
            current, nxt = messages[i], messages[i + 1]
            if current.sender_type == SenderType.USER and nxt.sender_type == SenderType.BOT:
                pairs.append({"question": current.message_text, "answer": nxt.message_text})
                i += 2
            else:
                i += 1
        return pairs

    @Slot(str)
    def select_session(self, session_id: str):
        """
        과거 세션을 선택 - 히스토리를 보여주는 것에 더해, 그 session_id로 커넥션을 다시 맺어서
        이 화면에서 바로 이어서 질문을 보낼 수 있게 한다 (EnsureSessionAsync가 upsert라
        같은 session_id로 다시 붙어도 DB 쪽엔 문제 없음).

        새 QueryClient에는 이 세션의 기존 대화를 history로 미리 채워 넘긴다 - 안 그러면
        서버 입장에서 이번이 "이 세션의 첫 메시지"로 보여 후속 질문 재작성(rewrite)이 안 켜진다.
        """
        if session_id == self._current_session_id:
            return  # 이미 이 세션에 붙어있으면 재연결 안 함

        try:
            self._messages = self._handler.get_messages(session_id)
        except Exception as e:
            self.errorOccurred.emit(f"메시지 조회 실패: {e}")
            return

        old_client = self._query_client
        if old_client is not None:
            old_client.close()

        history = self._build_history_pairs(self._messages)
        self._wire_query_client(QueryClient(session_id=session_id, history=history))
        self._current_session_id = session_id
        self._pending_domain = None

        self.currentSessionChanged.emit(session_id)
        self.messagesChanged.emit(self._messages)
        self.inputPromptChanged.emit(self.DOMAIN_PROMPT)
        self.start_connection()

    @property
    def current_session_id(self) -> Optional[str]:
        return self._current_session_id