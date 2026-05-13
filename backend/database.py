"""SQLite 数据库管理器（单例）"""
import json
import logging
import os
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "smarttraffic.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


class Database:
    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        if not os.path.exists(SCHEMA_PATH):
            return
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()
        self._migrate()

    def _migrate(self):
        """为旧数据库添加五层模型扩展列"""
        new_cols = {
            "src_mac": "VARCHAR(17) DEFAULT ''",
            "dst_mac": "VARCHAR(17) DEFAULT ''",
            "frame_type": "VARCHAR(10) DEFAULT ''",
            "ttl": "INTEGER DEFAULT 0",
            "ip_version": "INTEGER DEFAULT 4",
            "ip_flags": "VARCHAR(10) DEFAULT ''",
            "tcp_flags": "VARCHAR(30) DEFAULT ''",
            "window_size": "INTEGER DEFAULT 0",
            "payload_size": "INTEGER DEFAULT 0",
            "analysis_json": "TEXT",
        }
        existing = {r[1] for r in self.conn.execute("PRAGMA table_info(classification)")}
        for col, col_def in new_cols.items():
            if col not in existing:
                try:
                    self.conn.execute(f"ALTER TABLE classification ADD COLUMN {col} {col_def}")
                    logger.info(f"[DB] 迁移: 添加列 classification.{col}")
                except Exception as e:
                    logger.warning(f"[DB] 迁移 {col} 失败: {e}")
        self.conn.commit()

    # ── 会话操作 ──

    def create_session(self, interface: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO capture_session (interface, start_time) VALUES (?, ?)",
            (interface, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        self.conn.commit()
        return cur.lastrowid

    def end_session(self, session_id: int, total_packets: int, total_bytes: int):
        self.conn.execute(
            "UPDATE capture_session SET end_time=?, total_packets=?, total_bytes=?, status='stopped' WHERE id=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total_packets, total_bytes, session_id),
        )
        self.conn.commit()

    def get_active_sessions(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM capture_session WHERE status='running' ORDER BY start_time DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_sessions(self, limit=50, date_from=None, date_to=None) -> list[dict]:
        query = "SELECT * FROM capture_session WHERE 1=1"
        params = []
        if date_from:
            query += " AND start_time >= ?"
            params.append(date_from)
        if date_to:
            query += " AND start_time <= ?"
            params.append(date_to + " 23:59:59")
        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: int) -> int:
        """删除会话及其关联的流和分类记录，返回删除的分类数"""
        cls_count = self.conn.execute(
            "SELECT COUNT(*) FROM classification WHERE session_id=?", (session_id,)
        ).fetchone()[0]
        self.conn.execute("DELETE FROM classification WHERE session_id=?", (session_id,))
        self.conn.execute("DELETE FROM flow WHERE session_id=?", (session_id,))
        self.conn.execute("DELETE FROM capture_session WHERE id=?", (session_id,))
        self.conn.commit()
        return cls_count

    def get_available_dates(self) -> list[str]:
        """返回有数据的日期列表"""
        rows = self.conn.execute(
            "SELECT DISTINCT substr(start_time, 1, 10) AS d FROM capture_session ORDER BY d DESC LIMIT 60"
        ).fetchall()
        return [r["d"] for r in rows]

    def get_session_detail(self, session_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM capture_session WHERE id=?", (session_id,)
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        # 附加上该会话的分类统计
        cls_rows = self.conn.execute(
            "SELECT label, COUNT(*) AS cnt FROM classification WHERE session_id=? GROUP BY label",
            (session_id,),
        ).fetchall()
        result["category_distribution"] = {r["label"]: r["cnt"] for r in cls_rows}
        result["total_classifications"] = sum(r["cnt"] for r in cls_rows)
        return result

    # ── 流操作 ──

    def upsert_flow(self, session_id: int, flow) -> int:
        """插入或更新流，返回 flow 数据库 ID"""
        cur = self.conn.execute(
            "SELECT id, pkt_count, total_bytes FROM flow WHERE flow_id=?",
            (flow.flow_id,),
        )
        row = cur.fetchone()
        import time
        now = time.time()

        if row:
            self.conn.execute(
                "UPDATE flow SET pkt_count=?, total_bytes=?, last_seen=? WHERE id=?",
                (len(flow.packets), flow.total_bytes, now, row["id"]),
            )
            self.conn.commit()
            return row["id"]
        else:
            cur = self.conn.execute(
                """INSERT INTO flow (session_id, flow_id, src_ip, dst_ip, src_port, dst_port,
                   protocol, pkt_count, total_bytes, start_time, last_seen)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id, flow.flow_id, flow.src_ip, flow.dst_ip,
                    flow.src_port, flow.dst_port, flow.protocol,
                    len(flow.packets), flow.total_bytes,
                    getattr(flow, "start_time", now), now,
                ),
            )
            self.conn.commit()
            return cur.lastrowid

    # ── 分类记录 ──

    def insert_classification(
        self, session_id: int, flow_id: int, label: str,
        confidence: float, features, src_ip: str, dst_ip: str,
        src_port: int, dst_port: int, protocol: str,
        src_mac: str = "", dst_mac: str = "", frame_type: str = "",
        ttl: int = 0, ip_version: int = 4, ip_flags: str = "",
        tcp_flags: str = "", window_size: int = 0, payload_size: int = 0,
        analysis_json: str = "",
    ) -> int:
        import numpy as np
        feats_json = json.dumps(
            features.tolist() if isinstance(features, np.ndarray) else features or []
        )
        cur = self.conn.execute(
            """INSERT INTO classification
               (session_id, flow_id, label, confidence, features,
                src_mac, dst_mac, frame_type, ttl, ip_version, ip_flags,
                tcp_flags, window_size, payload_size, analysis_json,
                src_ip, dst_ip, src_port, dst_port, protocol)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?)""",
            (session_id, flow_id, label, confidence, feats_json,
             src_mac, dst_mac, frame_type, ttl, ip_version, ip_flags,
             tcp_flags, window_size, payload_size, analysis_json,
             src_ip, dst_ip, src_port, dst_port, protocol),
        )
        self.conn.commit()
        return cur.lastrowid

    def query_history(
        self, session_id=None, label=None, date_from=None, date_to=None,
        limit=100, offset=0,
    ) -> list[dict]:
        query = "SELECT * FROM classification WHERE 1=1"
        params = []
        if session_id is not None:
            query += " AND session_id=?"
            params.append(session_id)
        if label:
            query += " AND label=?"
            params.append(label)
        if date_from:
            query += " AND created_at >= ?"
            params.append(date_from)
        if date_to:
            query += " AND created_at <= ?"
            params.append(date_to + " 23:59:59")
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_statistics(self, session_id: int) -> dict:
        """返回某会话的统计: 各类别数量、总包数、字节数"""
        rows = self.conn.execute(
            "SELECT label, COUNT(*) AS cnt FROM classification WHERE session_id=? GROUP BY label",
            (session_id,),
        ).fetchall()
        dist = {r["label"]: r["cnt"] for r in rows}

        session = self.conn.execute(
            "SELECT total_packets, total_bytes FROM capture_session WHERE id=?",
            (session_id,),
        ).fetchone()

        return {
            "category_distribution": dist,
            "total_packets": session["total_packets"] if session else 0,
            "total_bytes": session["total_bytes"] if session else 0,
        }

    # ── 特征导出 ──

    def export_training_data(self, limit=10000):
        """导出 features + label 用于训练新模型"""
        rows = self.conn.execute(
            "SELECT features, label FROM classification WHERE features IS NOT NULL AND features != '' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        import numpy as np
        X_list, y_list = [], []
        for r in rows:
            try:
                feats = json.loads(r["features"])
                if len(feats) == 30:
                    X_list.append(feats)
                    y_list.append(r["label"])
            except (json.JSONDecodeError, TypeError):
                continue
        if not X_list:
            return np.array([]), np.array([])
        return np.array(X_list), np.array(y_list)

    def get_history_count(self, session_id=None, label=None, date_from=None, date_to=None) -> int:
        query = "SELECT COUNT(*) AS total FROM classification WHERE 1=1"
        params = []
        if session_id is not None:
            query += " AND session_id=?"
            params.append(session_id)
        if label:
            query += " AND label=?"
            params.append(label)
        if date_from:
            query += " AND created_at >= ?"
            params.append(date_from)
        if date_to:
            query += " AND created_at <= ?"
            params.append(date_to + " 23:59:59")
        row = self.conn.execute(query, params).fetchone()
        return row["total"] if row else 0


db = Database()
