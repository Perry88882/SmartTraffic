-- SmartTraffic 数据库初始化脚本
-- 数据库: SQLite3
-- 路径: backend/data/smarttraffic.db

CREATE TABLE IF NOT EXISTS capture_session (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    interface       VARCHAR(100)  NOT NULL,
    start_time      DATETIME      NOT NULL,
    end_time        DATETIME,
    total_packets   INTEGER       DEFAULT 0,
    total_bytes     INTEGER       DEFAULT 0,
    status          VARCHAR(20)   DEFAULT 'running',
    created_at      DATETIME      DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS flow (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER       NOT NULL,
    flow_id         VARCHAR(200)  NOT NULL UNIQUE,
    src_ip          VARCHAR(45)   NOT NULL,
    dst_ip          VARCHAR(45)   NOT NULL,
    src_port        INTEGER,
    dst_port        INTEGER,
    protocol        VARCHAR(10),
    pkt_count       INTEGER       DEFAULT 0,
    total_bytes     INTEGER       DEFAULT 0,
    start_time      REAL,
    last_seen       REAL,
    created_at      DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES capture_session(id)
);

CREATE TABLE IF NOT EXISTS classification (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER       NOT NULL,
    flow_id         INTEGER,
    label           VARCHAR(20)   NOT NULL,
    confidence      REAL          NOT NULL,
    features        TEXT,
    src_ip          VARCHAR(45)   NOT NULL,
    dst_ip          VARCHAR(45)   NOT NULL,
    src_port        INTEGER,
    dst_port        INTEGER,
    protocol        VARCHAR(10),
    created_at      DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES capture_session(id),
    FOREIGN KEY (flow_id)    REFERENCES flow(id)
);

CREATE INDEX IF NOT EXISTS idx_session_status    ON capture_session(status);
CREATE INDEX IF NOT EXISTS idx_session_time      ON capture_session(start_time);
CREATE INDEX IF NOT EXISTS idx_flow_session      ON flow(session_id);
CREATE INDEX IF NOT EXISTS idx_flow_5tuple       ON flow(src_ip, dst_ip, src_port, dst_port, protocol);
CREATE INDEX IF NOT EXISTS idx_cls_session       ON classification(session_id);
CREATE INDEX IF NOT EXISTS idx_cls_label         ON classification(label);
CREATE INDEX IF NOT EXISTS idx_cls_created       ON classification(created_at);
CREATE INDEX IF NOT EXISTS idx_cls_session_label ON classification(session_id, label);
