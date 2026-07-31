"""
실행 진입점.

qasync로 Qt 이벤트 루프와 asyncio 이벤트 루프를 하나로 합친다.
그래야 gui/network_client.py의 QueryClient(내부적으로 client/app/api_server_client.py의
ApiServerClient를 그대로 씀)가 GUI를 안 막고 백그라운드에서 동작할 수 있다.

실행 방법 (반드시 프로젝트 루트, 즉 이 파일 기준 상위 폴더에서):
    python -m gui.main
"""
import asyncio
import sys

import qasync
from PySide6.QtWidgets import QApplication

from handler.real_db_handler import RealDbHandler
from gui.network_client import QueryClient
from gui.view import ChatWindow
from gui.viewmodel import ChatViewModel


def main():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    # 로그인 없이 실행 -> 전체 세션 조회(get_all_sessions) 기반. DB_HOST/DB_USER/DB_PASSWORD/DB_NAME
    # 환경변수가 설정돼 있어야 함 (DBServer와 동일한 컨벤션).
    handler = RealDbHandler()
    query_client = QueryClient()  # API_SERVER_HOST/API_SERVER_PORT 환경변수로 접속 대상 지정 가능
    viewmodel = ChatViewModel(handler, query_client)
    window = ChatWindow(viewmodel)
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()