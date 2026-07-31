from datetime import date


class ResponseRate:
    """응답률 카드에 필요한 값 모양"""

    def __init__(self, total_questions, answered_questions, response_rate_pct):
        self.total_questions = total_questions
        self.answered_questions = answered_questions
        self.response_rate_pct = response_rate_pct


class RagRatioItem:
    """원형그래프 조각 하나의 모양"""

    def __init__(self, target_index, count, percentage):
        self.target_index = target_index
        self.count = count
        self.percentage = percentage


class SessionTrendItem:
    """선그래프 점 하나의 모양"""

    def __init__(self, date, daily_sessions, cumulative_sessions):
        self.date = date
        self.daily_sessions = daily_sessions
        self.cumulative_sessions = cumulative_sessions