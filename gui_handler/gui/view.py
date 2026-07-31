"""
PySide6 View - 와이어프레임 기준:
  - 좌상단 토글 버튼으로 사이드바(과거 대화 목록) 여닫기
  - 메인: 말풍선 채팅 (USER=오른쪽, Response=왼쪽), 대화 없을 때 "RAG project" placeholder
  - 하단: 입력창 (Enter로 전송)

ViewModel의 Signal만 구독한다. 비즈니스 로직(DB 조회, 네트워크 전송)은 전혀 없다.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from handler.models import ChatMessage, ChatSession, SenderType
from gui.viewmodel import ChatViewModel

BUBBLE_MAX_WIDTH = 420


def _make_bubble(text: str, caption: str, is_user: bool) -> QWidget:
    """말풍선 하나(텍스트 + 위/아래 캡션(USER/Response))를 만든다."""
    bubble_label = QLabel(text)
    bubble_label.setWordWrap(True)
    bubble_label.setMaximumWidth(BUBBLE_MAX_WIDTH)
    bubble_label.setStyleSheet(
        "background:%s; border:1px solid #999; border-radius:8px; padding:8px 12px;"
        % ("#eeeeee" if is_user else "#ffffff")
    )

    caption_label = QLabel(caption)
    caption_label.setStyleSheet("color:#2222aa; font-size:11px;")
    caption_label.setAlignment(Qt.AlignRight if is_user else Qt.AlignLeft)

    column = QVBoxLayout()
    column.setSpacing(2)
    column.addWidget(bubble_label, alignment=Qt.AlignRight if is_user else Qt.AlignLeft)
    column.addWidget(caption_label)

    row = QHBoxLayout()
    row.setContentsMargins(0, 4, 0, 4)
    if is_user:
        row.addStretch(1)
        row.addLayout(column)
    else:
        row.addLayout(column)
        row.addStretch(1)

    wrapper = QWidget()
    wrapper.setLayout(row)
    return wrapper


class ChatWindow(QWidget):
    def __init__(self, viewmodel: ChatViewModel):
        super().__init__()
        self.setWindowTitle("RAG project")
        self.resize(1000, 650)
        self.vm = viewmodel

        self._build_ui()
        self._connect_signals()

        self.vm.load_sessions()
        self.vm.start_connection()

    # ---------------- UI 구성 ----------------
    def _build_ui(self):
        self.toggle_button = QPushButton("≡")
        self.toggle_button.setFixedWidth(32)
        self.toggle_button.clicked.connect(self._toggle_sidebar)

        self.new_chat_button = QPushButton("+ 새 채팅")
        self.new_chat_button.clicked.connect(self._on_new_chat)

        self.complaint_button = QPushButton("고소장 작성")
        self.complaint_button.clicked.connect(self._on_open_complaint)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.toggle_button)
        top_bar.addWidget(self.new_chat_button)
        top_bar.addWidget(self.complaint_button)
        top_bar.addStretch(1)

        # 사이드바 (과거 대화 목록)
        self.session_list = QListWidget()
        self.session_list.setFixedWidth(200)
        self.session_list.currentItemChanged.connect(self._on_session_selected)

        # 채팅 영역
        self.placeholder_label = QLabel("RAG project")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setStyleSheet("color:#cccccc; font-size:28px;")

        self.chat_column = QVBoxLayout()
        self.chat_column.setAlignment(Qt.AlignTop)
        self.chat_column.addWidget(self.placeholder_label)

        chat_container = QWidget()
        chat_container.setLayout(self.chat_column)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setWidget(chat_container)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText(ChatViewModel.DOMAIN_PROMPT)
        self.input_box.returnPressed.connect(self._on_send)

        main_column = QVBoxLayout()
        main_column.addLayout(top_bar)
        main_column.addWidget(self.chat_scroll, 1)
        main_column.addWidget(self.input_box)

        main_widget = QWidget()
        main_widget.setLayout(main_column)

        root = QHBoxLayout(self)
        root.addWidget(self.session_list)
        root.addWidget(main_widget, 1)

    def _connect_signals(self):
        self.vm.sessionsChanged.connect(self._on_sessions_changed)
        self.vm.messagesChanged.connect(self._on_messages_changed)
        self.vm.domainMessageAdded.connect(lambda text: self._append_bubble(text, "분야", is_user=True))
        self.vm.userMessageAdded.connect(lambda text: self._append_bubble(text, "USER", is_user=True))
        self.vm.botMessageAdded.connect(lambda text: self._append_bubble(text, "Response", is_user=False))
        self.vm.botMessageAdded.connect(lambda _text: self.vm.load_sessions())
        self.vm.connectionStatusChanged.connect(self._on_connection_status_changed)
        self.vm.errorOccurred.connect(self._on_error)
        self.vm.chatReset.connect(self._on_chat_reset)
        self.vm.inputPromptChanged.connect(self.input_box.setPlaceholderText)

    # ---------------- 동작 ----------------
    def _toggle_sidebar(self):
        self.session_list.setVisible(not self.session_list.isVisible())

    def _on_send(self):
        text = self.input_box.text()
        if not text.strip():
            return
        self.input_box.clear()
        self.vm.send_message(text)

    def _on_new_chat(self):
        self.session_list.clearSelection()
        self.vm.start_new_chat()

    def _on_open_complaint(self):
        # 매번 새 다이얼로그 인스턴스 - 이전에 열었던 폼 내용이 남지 않도록, 시그널 중복 연결도 방지
        from gui.complaint_dialog import ComplaintDialog

        dialog = ComplaintDialog(self.vm, parent=self)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.show()

    def _on_chat_reset(self):
        self._clear_chat_area()

    def _clear_chat_area(self):
        while self.chat_column.count():
            item = self.chat_column.takeAt(0)
            widget = item.widget()
            # placeholder_label은 계속 재사용하는 위젯이라 파괴하면 안 됨 - 레이아웃에서만 뺀다
            if widget is not None and widget is not self.placeholder_label:
                widget.deleteLater()
        self.chat_column.addWidget(self.placeholder_label)
        self.placeholder_label.show()

    def _clear_placeholder(self):
        if self.placeholder_label.isVisible():
            self.placeholder_label.hide()

    def _append_bubble(self, text: str, caption: str, is_user: bool):
        self._clear_placeholder()
        self.chat_column.addWidget(_make_bubble(text, caption, is_user))

    # ---------------- ViewModel 시그널 핸들러 ----------------
    def _on_sessions_changed(self, sessions: list[ChatSession]):
        self.session_list.clear()
        for s in sessions:
            item = QListWidgetItem(s.preview or s.title or s.session_id)
            item.setData(Qt.UserRole, s.session_id)
            self.session_list.addItem(item)

    def _on_session_selected(self, current: QListWidgetItem, _previous):
        if current is None:
            return
        session_id = current.data(Qt.UserRole)
        self.vm.select_session(session_id)

    def _on_messages_changed(self, messages: list[ChatMessage]):
        # 사이드바에서 과거 세션을 선택했을 때 - 지금 채팅 영역을 그 히스토리로 통째로 교체
        self._clear_chat_area()

        if not messages:
            return

        self._clear_placeholder()
        for m in messages:
            is_user = m.sender_type == SenderType.USER
            caption = "USER" if is_user else "Response"
            self.chat_column.addWidget(_make_bubble(m.message_text, caption, is_user))

    def _on_connection_status_changed(self, status: str):
        title = {"connecting": "RAG project (연결 중...)",
                 "connected": "RAG project",
                 "failed": "RAG project (연결 실패)"}.get(status, "RAG project")
        self.setWindowTitle(title)

    def _on_error(self, message: str):
        self._clear_placeholder()
        error_label = QLabel(f"[오류] {message}")
        error_label.setStyleSheet("color:#cc0000;")
        self.chat_column.addWidget(error_label)