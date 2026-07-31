import os
import pymysql
from pymysql.cursors import DictCursor

class StatsHandler:
    """
    통계창(PySide6) 전용 DB 접속 클래스,
    채팅 흐름(Client-API-Main-DBServer)과 완전히 독립적으로 동작함.
    - 연결 정보는 환경변수로 받음 (DB_HOST/DB_USER/DB_PASSWORD/DB_NAME)
    - 조회 전용(Read) 메서드만 추가하는 구조
    """

    def __init__(self):
        self.host = os.environ["DB_HOST"]
        self.user = os.environ["DB_USER"]
        self.password = os.environ["DB_PASSWORD"]
        self.db = os.environ["DB_NAME"]
        self.conn = None

    def connect(self):
        self.conn = pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            db=self.db,
            charset="utf8mb4",
            cursorclass=DictCursor,
        )

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

   # === 연결(connect)하고 끝나면 자동으로 끊는(close) 방식 ===

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

   # ==== 여기부터 통계용 조회 메서드 ====

    def get_response_rate(self):
        """
        전체 USER 메시지 대비 BOT 메시지 비율로 응답률을 간접 계산.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT "
                "    SUM(sender_type = 'USER') AS total_questions, "
                "    SUM(sender_type = 'BOT') AS answered_questions, "
                "    ROUND(SUM(sender_type = 'BOT') / SUM(sender_type = 'USER') * 100, 1) "
                "        AS response_rate_pct "
                "FROM chat_messages"
            )
            return cursor.fetchone()

    def get_rag_selection_ratio(self):
        """
        카테고리(target_index)별 검색 횟수와 전체 대비 비율(%)을 가져옴.
        판결문(precedents)/법령(statutes)/심결례(adjudications)/유권해석(interpretations) 비교용.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT "
                "    target_index, "
                "    COUNT(*) AS count, "
                "    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS percentage "
                "FROM rag_retrieval_logs "
                "GROUP BY target_index "
                "ORDER BY count DESC"
            )
            return cursor.fetchall()

    def get_cumulative_sessions(self):
        """
        날짜별 상담 세션 수와 누적치를 가져옴 (그래프용).
        user_id가 전부 NULL이라 '누적 이용자'가 아니라 '누적 상담 건수'로 집계함.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT "
                "    DATE(created_at) AS date, "
                "    COUNT(*) AS daily_sessions, "
                "    SUM(COUNT(*)) OVER (ORDER BY DATE(created_at)) AS cumulative_sessions "
                "FROM chat_sessions "
                "GROUP BY DATE(created_at) "
                "ORDER BY date"
            )
            return cursor.fetchall()
