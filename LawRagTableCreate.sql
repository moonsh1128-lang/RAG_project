-- 1. 대화 세션 테이블 (chat_sessions)

CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 메시지 이력 테이블 (chat_messages)
CREATE TABLE chat_messages (
    message_id VARCHAR(100) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    sender_type VARCHAR(20) NOT NULL, -- 'USER' 또는 'BOT'
    message_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chat_session 
        FOREIGN KEY (session_id) 
        REFERENCES chat_sessions (session_id) 
        ON DELETE CASCADE
);

-- 3. RAG 검색 상세 로그 테이블 (rag_retrieval_logs)
CREATE TABLE rag_retrieval_logs (
    log_id VARCHAR(100) PRIMARY KEY,
    message_id VARCHAR(100) NOT NULL,
    search_query VARCHAR(500) NOT NULL, -- 형태소 분석/키워드 추출 후 실제 검색에 사용된 쿼리
    target_index VARCHAR(100),          -- 대상 DB 인덱스 (예: statutes, precedents)
    top_k INT NOT NULL,                 -- 가져오도록 설정한 문서 개수
    retrieved_chunks TEXT NOT NULL,     -- 검색된 문서 조각 상세 정보 (JSON 형식의 문자열로 저장)
    retrieval_time_ms INT,              -- 검색 소요 시간 (밀리초)
    CONSTRAINT fk_chat_message 
        FOREIGN KEY (message_id) 
        REFERENCES chat_messages (message_id) 
        ON DELETE CASCADE
);
