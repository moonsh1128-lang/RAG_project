import os
import pymysql
from pymysql.cursors import DictCursor

class DBHandler:
    """
    DB로부터 값을 가져오는 역할만 담당.
    - 연결 정보는 환경변수로 받음 (DBServer의 DB_HOST/DB_USER/DB_PASSWORD/DB_NAME 컨벤션과 통일)
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

    #=== 연결(connect)하고 끝나면 자동으로 끊는 (close) 방식 ===

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exe_type, exc_val, exc_tb):
        self.close()

    #==== 여기부터 실제 조회 메서드를 하나씩 추가 ====

    def get_all_sessions(self):
        """
        모든 세션 목록을  가져옴 (chat_sessions 테이블 전체 조회)
        """
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM chat_sessions ORDER BY created_at")
            return cursor.fetchall()

    #---추가된 메서드---

    def get_messages_by_session(self, session_id: str):
        """
        특정 세션의 대화 기록 전체를 시간순으로 가져옴 (chat_messages 테이블)
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM chat_messages WHERE session_id = %s ORDER BY created_at",
                (session_id,),
            )
            return cursor.fetchall()

    def get_logs_by_message(self, message_id: str):
        """
        특정 메시지에 딸린 RAG 검색 로그를 가져옴 (rag_retrieval_logs 테이블)
        """
        # rag_retrieval_logs 테이블에는 created_at 컬럼이 없다(LawRagTableCreate 기준).
        # 시간 기준 정렬이 불가능하므로 log_id로 정렬해 결과 순서만 고정한다.
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM rag_retrieval_logs WHERE message_id = %s ORDER BY log_id",
                (message_id,),
            )
            return cursor.fetchall()

    #==== 세션 조회 ====

    def get_session(self, session_id: str):
        """
        세션 1건을 가져옴. 없으면 None.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM chat_sessions WHERE session_id = %s",
                (session_id,),
            )
            return cursor.fetchone()

    def get_sessions_by_user(self, user_id: str):
        """
        특정 사용자의 세션 목록을 최신순으로 가져옴 (세션 목록 화면용)
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM chat_sessions WHERE user_id = %s ORDER BY updated_at DESC",
                (user_id,),
            )
            return cursor.fetchall()

    #==== 메시지 조회 ====

    def get_message(self, message_id: str):
        """
        메시지 1건을 가져옴. 없으면 None.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM chat_messages WHERE message_id = %s",
                (message_id,),
            )
            return cursor.fetchone()

    def get_latest_message(self, session_id: str):
        """
        세션의 마지막 메시지 1건을 가져옴 (세션 목록의 미리보기 문구용). 없으면 None.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM chat_messages WHERE session_id = %s "
                "ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            )
            return cursor.fetchone()

    def search_messages(self, keyword: str, limit: int = 50):
        """
        대화 내용(message_text)에서 키워드를 포함한 메시지를 최신순으로 검색.
        %가 붙은 검색어도 값으로만 전달되므로 SQL 구조는 바뀌지 않음.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM chat_messages WHERE message_text LIKE %s "
                "ORDER BY created_at DESC LIMIT %s",
                (f"%{keyword}%", limit),
            )
            return cursor.fetchall()

    #==== RAG 로그 조회 ====

    def get_logs_by_session(self, session_id: str):
        """
        세션 전체의 RAG 검색 로그를 시간순으로 가져옴.
        로그에는 시간 컬럼이 없으므로 chat_messages와 JOIN해서 메시지 시간으로 정렬한다.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT l.*, m.created_at AS message_created_at "
                "FROM rag_retrieval_logs l "
                "JOIN chat_messages m ON m.message_id = l.message_id "
                "WHERE m.session_id = %s "
                "ORDER BY m.created_at, l.log_id",
                (session_id,),
            )
            return cursor.fetchall()

    def get_conversation_with_logs(self, session_id: str):
        """
        세션의 메시지와 각 메시지의 RAG 로그를 쿼리 1번으로 가져옴 (대화 상세 화면용).
        메시지마다 get_logs_by_message()를 반복 호출하면 쿼리가 메시지 수만큼 늘어나므로
        (N+1 문제) LEFT JOIN 한 번으로 처리한다.
        로그가 없는 메시지는 로그 컬럼이 전부 None으로 채워져 함께 반환된다.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT m.message_id, m.session_id, m.sender_type, m.message_text, "
                "       m.created_at, "
                "       l.log_id, l.search_query, l.target_index, l.top_k, "
                "       l.retrieved_chunks, l.retrieval_time_ms "
                "FROM chat_messages m "
                "LEFT JOIN rag_retrieval_logs l ON l.message_id = m.message_id "
                "WHERE m.session_id = %s "
                "ORDER BY m.created_at, l.log_id",
                (session_id,),
            )
            return cursor.fetchall()

    #==== 통계 조회 (PySide6 통계 화면용) ====

    def get_summary_counts(self):
        """
        세션/메시지/로그 전체 건수를 한 행으로 가져옴.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT (SELECT COUNT(*) FROM chat_sessions)      AS session_count, "
                "       (SELECT COUNT(*) FROM chat_messages)      AS message_count, "
                "       (SELECT COUNT(*) FROM rag_retrieval_logs) AS log_count"
            )
            return cursor.fetchone()

    def get_index_stats(self):
        """
        카테고리(target_index)별 검색 횟수와 소요 시간 통계.
        판결문(precedents)/법령(statutes)/심결례(decisions)/유권해석(interpretations) 비교용.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT target_index, "
                "       COUNT(*)                        AS search_count, "
                "       ROUND(AVG(retrieval_time_ms))   AS avg_time_ms, "
                "       MAX(retrieval_time_ms)          AS max_time_ms, "
                "       ROUND(AVG(top_k), 1)            AS avg_top_k "
                "FROM rag_retrieval_logs "
                "GROUP BY target_index "
                "ORDER BY search_count DESC"
            )
            return cursor.fetchall()

    def get_daily_message_counts(self, days: int = 30):
        """
        최근 N일간 일자별 메시지 수를 USER/BOT로 나눠서 가져옴 (추이 그래프용)
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT DATE(created_at) AS day, "
                "       COUNT(*)                                        AS total, "
                "       SUM(sender_type = 'USER')                       AS user_count, "
                "       SUM(sender_type = 'BOT')                        AS bot_count "
                "FROM chat_messages "
                "WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY) "
                "GROUP BY DATE(created_at) "
                "ORDER BY day",
                (days,),
            )
            return cursor.fetchall()

    def get_slowest_retrievals(self, limit: int = 10):
        """
        검색 소요 시간이 긴 로그를 순서대로 가져옴 (성능 병목 확인용)
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT l.log_id, l.search_query, l.target_index, l.top_k, "
                "       l.retrieval_time_ms, m.session_id, m.created_at "
                "FROM rag_retrieval_logs l "
                "JOIN chat_messages m ON m.message_id = l.message_id "
                "WHERE l.retrieval_time_ms IS NOT NULL "
                "ORDER BY l.retrieval_time_ms DESC "
                "LIMIT %s",
                (limit,),
            )
            return cursor.fetchall()
