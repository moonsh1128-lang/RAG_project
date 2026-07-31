from PySide6.QtCore import QObject, Signal

from stats_handler import StatsHandler
from models import ResponseRate, RagRatioItem, SessionTrendItem


class StatsViewModel(QObject):
    """
    Handler에서 값을 받아 Model 모양으로 정리하고,
    View에게 '데이터 바뀌었다'고 신호(Signal)를 보내는 역할.
    View가 어떻게 생겼는지는 전혀 모름.
    """

    response_rate_changed = Signal(object)
    rag_ratio_changed = Signal(object)
    session_trend_changed = Signal(object)

    def load(self):
        """DB에서 값을 가져와 Model로 변환하고, 각 신호를 발생시킴"""
        with StatsHandler() as db:
            rate_row = db.get_response_rate()
            ratio_rows = db.get_rag_selection_ratio()
            session_rows = db.get_cumulative_sessions()

        rate = ResponseRate(
            total_questions=int(rate_row["total_questions"]),
            answered_questions=int(rate_row["answered_questions"]),
            response_rate_pct=float(rate_row["response_rate_pct"]),
        )
        ratio = [
            RagRatioItem(r["target_index"], int(r["count"]), float(r["percentage"]))
            for r in ratio_rows
        ]
        trend = [
            SessionTrendItem(r["date"], int(r["daily_sessions"]), int(r["cumulative_sessions"]))
            for r in session_rows
        ]

        self.response_rate_changed.emit(rate)
        self.rag_ratio_changed.emit(ratio)
        self.session_trend_changed.emit(trend)