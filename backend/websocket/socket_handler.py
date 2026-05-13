"""
WebSocket 事件处理 — 集成真实数据管道
Pipeline: CaptureManager → packet_parser → flow_reassembly → feature_extractor → inference
"""
import logging
import time
from collections import defaultdict
from datetime import datetime

import eventlet
from flask import request
from flask_socketio import Namespace, emit

from config import CLASSIFICATION_INTERVAL, LABELS, STATISTICS_INTERVAL
from database import db
from pipeline.capture_manager import CaptureManager
from pipeline.flow_reassembly import FlowReassembler
from pipeline.feature_extractor import extract_features
from pipeline.inference import classifier
from pipeline.packet_parser import parse_packet

logger = logging.getLogger(__name__)


class SocketManager:
    def __init__(self):
        self._running = False
        self._thread = None
        self._start_time = 0.0
        self._total_bytes = 0
        self._total_packets = 0
        self._category_counts = defaultdict(int)
        self._socketio = None
        self._session_id = None
        self._capture = CaptureManager()
        self._reassembler = FlowReassembler()

    def init_app(self, socketio):
        self._socketio = socketio

    @property
    def mode(self):
        return self._capture.mode

    @property
    def is_running(self):
        return self._running

    def start(self, interface: str):
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._total_bytes = 0
        self._total_packets = 0
        self._category_counts = defaultdict(int)
        self._reassembler = FlowReassembler()
        self._capture.start(interface)
        self._session_id = db.create_session(interface)
        self._thread = self._socketio.start_background_task(self._run)
        logger.info(f"[Socket] 已启动, 接口={interface}, 模式={self._capture.mode}, 会话ID={self._session_id}")

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._capture.stop()
        if self._session_id:
            db.end_session(self._session_id, self._total_packets, self._total_bytes)
        logger.info(f"[Socket] 已停止, 总包数={self._total_packets}, 总字节={self._total_bytes}")

    def _run(self):
        last_cls = 0
        last_stats = 0
        last_cleanup = 0
        while self._running:
            now = time.time()
            self._process_packets()

            if now - last_cls >= CLASSIFICATION_INTERVAL:
                self._emit_classification()
                last_cls = now
            if now - last_stats >= STATISTICS_INTERVAL:
                self._emit_statistics()
                last_stats = now
            if now - last_cleanup >= 30:
                n = self._reassembler.cleanup_stale_flows()
                if n > 0:
                    logger.debug(f"[Socket] 清理 {n} 条过期流, 当前流表大小={self._reassembler.flow_count}")
                last_cleanup = now
            eventlet.sleep(0.3)

    def _process_packets(self):
        """从抓包队列消费数据包，经管道处理后推送并写入数据库"""
        q = self._capture.packet_queue
        while not q.empty():
            try:
                pkt = q.get_nowait()
            except Exception:
                break

            # 如果数据包已经是解析过的 dict（来自模拟模式），直接使用
            # 如果是 scapy 原始包（来自真实抓包），需要先解析
            if isinstance(pkt, dict):
                parsed = pkt
            else:
                parsed = parse_packet(pkt)
                if parsed is None:
                    continue

            self._total_packets += 1
            self._total_bytes += parsed.get("length", 0)

            # 流重组
            flow = self._reassembler.process_packet(parsed)

            # 每个包都进行推理（特征提取器对单包流也有合理的特征计算）
            # 特征提取
            features = extract_features(flow)

            # 推理分类
            result = classifier.predict(features)

            # 写入数据库
            flow_db_id = None
            try:
                flow_db_id = db.upsert_flow(self._session_id, flow)
                db.insert_classification(
                    session_id=self._session_id,
                    flow_id=flow_db_id,
                    label=result["label"],
                    confidence=result["confidence"],
                    features=features,
                    src_ip=parsed["src_ip"],
                    dst_ip=parsed["dst_ip"],
                    src_port=parsed["src_port"],
                    dst_port=parsed["dst_port"],
                    protocol=parsed["protocol"],
                )
            except Exception as e:
                logger.error(f"[Socket] 数据库写入失败: {e}")

            self._category_counts[result["label"]] += 1

    def _emit_classification(self):
        """从数据库取最新分类记录推送"""
        try:
            records = db.query_history(session_id=self._session_id, limit=1)
            if records:
                rec = records[0]
                msg = {
                    "type": "classification",
                    "data": {
                        "timestamp": rec["created_at"],
                        "src_ip": rec["src_ip"],
                        "dst_ip": rec["dst_ip"],
                        "src_port": rec["src_port"],
                        "dst_port": rec["dst_port"],
                        "protocol": rec["protocol"],
                        "label": rec["label"],
                        "confidence": round(rec["confidence"], 4),
                    },
                }
                self._socketio.emit("classification", msg, namespace="/")
        except Exception as e:
            logger.error(f"[Socket] 分类推送失败: {e}")

    def _emit_statistics(self):
        elapsed = max(int(time.time() - self._start_time), 1)
        msg = {
            "type": "statistics",
            "data": {
                "total_bytes": self._total_bytes,
                "current_rate": int(self._total_bytes / elapsed),
                "total_packets": self._total_packets,
                "duration_seconds": elapsed,
                "category_distribution": {
                    k: self._category_counts.get(k, 0) for k in LABELS
                },
            },
        }
        self._socketio.emit("statistics", msg, namespace="/")


socket_manager = SocketManager()


class SmartTrafficNamespace(Namespace):
    def on_connect(self):
        logger.info(f"[SocketIO] 客户端连接: {request.sid}")
        emit("welcome", {"message": "已连接"})

    def on_disconnect(self):
        logger.info(f"[SocketIO] 客户端断开: {request.sid}")
