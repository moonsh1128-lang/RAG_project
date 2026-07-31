"""
client/app/api_server_client.py의 ApiServerClient(asyncio 기반)를
PySide6 GUI(Qt 이벤트 루프)에서 그대로 쓰기 위한 래퍼.

ApiServerClient 자체는 수정하지 않는다 (이미 전체 체인에서 검증된 코드).
qasync로 asyncio 이벤트 루프와 Qt 이벤트 루프를 하나로 합쳐서, connect/send_query를
Qt 시그널/슬롯 흐름 안에서 await 없이(콜백 형태로) 쓸 수 있게만 감싼다.
"""
import asyncio
import os

from PySide6.QtCore import QObject, Signal

from client.app.api_server_client import ApiServerClient

API_SERVER_HOST = os.environ.get("API_SERVER_HOST", "127.0.0.1")
API_SERVER_PORT = int(os.environ.get("API_SERVER_PORT", "9000"))


class QueryClient(QObject):
    """GUI가 실제로 상호작용하는 대상. ApiServerClient를 내부에 들고 있다."""

    connected = Signal()
    connectFailed = Signal(str)
    responseReceived = Signal(str)   # 최종 답변 텍스트 ({"result": ...}의 result)
    errorOccurred = Signal(str)
    documentGenerated = Signal(str)  # 완성된 고소장 텍스트 ({"document": ...}의 document)
    complaintFailed = Signal(str)

    def __init__(
        self,
        host: str = API_SERVER_HOST,
        port: int = API_SERVER_PORT,
        session_id: str | None = None,
        history: list[dict] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._client = ApiServerClient(host, port)
        if session_id:
            # ApiServerClient가 생성 시점에 새 uuid를 만들어두는데, 과거 세션을 이어가려면
            # 그 자리를 우리가 원하는 기존 session_id로 덮어써야 한다. ApiServerClient 자체는
            # 수정하지 않고(공용 코드), 평범한 속성이라 밖에서 바로 덮어쓸 수 있다.
            self._client.session_id = session_id
        if history:
            # 과거 세션을 이어갈 때, DB에서 불러온 이전 대화를 ApiServerClient의 내부 상태
            # (_history/_message_count)에 미리 채워둔다. 이걸 안 하면 새 커넥션은 항상
            # message_count=0으로 시작해서, 실제로는 몇 번째 대화든 서버 입장에선 "첫 질문"으로
            # 보여 후속 질문 재작성(rewrite)이 안 켜진다.
            self._client._history = history
            self._client._message_count = len(history)

    @property
    def session_id(self) -> str:
        return self._client.session_id

    def connect_to_server(self) -> None:
        """연결 시도를 비동기로 예약한다. 결과는 connected/connectFailed 시그널로 온다."""
        asyncio.ensure_future(self._connect())

    async def _connect(self) -> None:
        try:
            await self._client.connect()
            self.connected.emit()
        except Exception as e:
            self.connectFailed.emit(f"API Server 연결 실패: {e}")

    def send(self, rag_selector_query: str, question: str) -> None:
        """1단계(분야)/2단계(상황) 텍스트를 각각 받아 전송한다."""
        asyncio.ensure_future(self._send(rag_selector_query, question))

    async def _send(self, rag_selector_query: str, question: str) -> None:
        try:
            response = await self._client.send_query(
                rag_selector_query=rag_selector_query, question=question
            )
        except Exception as e:
            self.errorOccurred.emit(f"전송 실패: {e}")
            return

        if "result" in response:
            self.responseReceived.emit(response["result"])
        elif "error" in response:
            self.errorOccurred.emit(response["error"])
        else:
            # 지금 프로토콜상 응답은 항상 "result" 아니면 "error"라 여기 오면 안 됨 - 방어적으로만 처리
            self.errorOccurred.emit(f"알 수 없는 응답 형식: {response}")

    def close(self) -> None:
        asyncio.ensure_future(self._client.close())

    def send_complaint(self, fields: dict) -> None:
        """고소장 생성 요청 - 기존 채팅(send)과는 완전히 별개 경로."""
        asyncio.ensure_future(self._send_complaint(fields))

    async def _send_complaint(self, fields: dict) -> None:
        try:
            response = await self._client.send_complaint(fields)
        except Exception as e:
            self.complaintFailed.emit(f"고소장 생성 실패: {e}")
            return

        if "document" in response:
            self.documentGenerated.emit(response["document"])
        elif "error" in response:
            self.complaintFailed.emit(response["error"])
        else:
            self.complaintFailed.emit(f"알 수 없는 응답 형식: {response}")