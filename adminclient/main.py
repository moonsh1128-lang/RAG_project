import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from PySide6.QtWidgets import QApplication

from stats_viewmodel import StatsViewModel
from stats_view import StatsView


if __name__ == "__main__":
    app = QApplication(sys.argv)

    viewmodel = StatsViewModel()
    view = StatsView(viewmodel)   # View가 신호 연결부터 먼저 함
    view.show()

    viewmodel.load()              # 그 다음 데이터 로드 시작 (신호가 View에 전달됨)

    sys.exit(app.exec())