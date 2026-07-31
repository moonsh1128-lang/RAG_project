import os
import matplotlib
import matplotlib.font_manager as fm

# 프로젝트 안에 동봉된 한글 폰트를 자동으로 등록 (팀원 컴퓨터에 별도 설치 불필요)
_font_path = os.path.join(os.path.dirname(__file__), "fonts", "NanumGothic.ttf")
fm.fontManager.addfont(_font_path)
matplotlib.rcParams['font.family'] = fm.FontProperties(fname=_font_path).get_name()
matplotlib.rcParams['axes.unicode_minus'] = False

from PySide6.QtWidgets import QMainWindow, QWidget, QGridLayout, QLabel
from PySide6.QtCore import Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class StatsView(QMainWindow):
    """
    화면 그리기만 담당. DB나 SQL은 전혀 모름.
    ViewModel의 신호(Signal)를 받아서 화면만 갱신함.
    """

    def __init__(self, viewmodel):
        super().__init__()
        self.viewmodel = viewmodel
        self.setWindowTitle("법률 상담 RAG - 통계")
        self.resize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QGridLayout(central)

        self.response_rate_label = QLabel("응답률 불러오는 중...")
        self.response_rate_label.setAlignment(Qt.AlignCenter)
        self.response_rate_label.setStyleSheet(
            "font-size: 32px; font-weight: bold; padding: 20px;"
        )
        layout.addWidget(self.response_rate_label, 0, 0, 1, 2)

        self.pie_figure = Figure(figsize=(4, 4))
        self.pie_canvas = FigureCanvasQTAgg(self.pie_figure)
        layout.addWidget(self.pie_canvas, 1, 0)

        self.line_figure = Figure(figsize=(4, 4))
        self.line_canvas = FigureCanvasQTAgg(self.line_figure)
        layout.addWidget(self.line_canvas, 1, 1)

        # ViewModel의 신호(방송)를 View의 메서드(듣는 사람)와 연결
        self.viewmodel.response_rate_changed.connect(self.update_response_rate)
        self.viewmodel.rag_ratio_changed.connect(self.update_pie_chart)
        self.viewmodel.session_trend_changed.connect(self.update_line_chart)

    def update_response_rate(self, rate):
        self.response_rate_label.setText(
            f"응답률 {rate.response_rate_pct}%\n"
            f"(질문 {rate.total_questions}건 중 {rate.answered_questions}건 응답)"
        )

    def update_pie_chart(self, ratio_list):
        labels = [r.target_index for r in ratio_list]
        counts = [r.count for r in ratio_list]

        ax = self.pie_figure.add_subplot(111)
        ax.clear()
        ax.pie(counts, labels=labels, autopct="%1.1f%%")
        ax.set_title("Rag 선택 비율")
        self.pie_canvas.draw()

    def update_line_chart(self, trend_list):
        dates = [t.date.strftime("%m-%d") for t in trend_list]
        cumulative = [t.cumulative_sessions for t in trend_list]

        ax = self.line_figure.add_subplot(111)
        ax.clear()
        ax.plot(dates, cumulative, marker="o")
        ax.set_title("누적 상담 세션")
        ax.set_ylabel("누적 건수")
        self.line_canvas.draw()