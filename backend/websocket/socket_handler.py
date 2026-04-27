"""
WebSocket 事件处理
通过 SocketIO 向前端实时推送分类结果和统计汇总。
"""

import logging
import random
import threading
import time
from datetime import datetime

import eventlet
from flask import request
from flask_socketio import Namespace, emit

from config import (
    CLASSIFICATION_INTERVAL,
    LABELS,
    SIMULATED_PUBLIC_IPS,
    SIMULATED_SUBNETS,
    STATISTICS_INTERVAL,
)

logger = logging.getLogger(__name__)

# 模拟协议列表
PROTOCOLS = ["TCP", "UDP"]


def _random_ip(is_src: bool = True) -> str:
    """生成随机模拟 IP 地址"""
    subnet = random.choice(SIMULATED_SUBNETS)
    host = random.randint(2, 254)
    return f"{subnet}{host}"


def _random_port(is_server: bool = False) -> int:
    """生成随机端口号；服务端常用端口单独处理"""
    if is_server:
        return random.choice([443, 80, 8080, 8443, 53, 25, 110, 993, 22, 3389])
    return random.randint(1024, 65535)


def _generate_classification() -> dict:
    """生成一条模拟分类结果"""
    dst_ip = random.choice(SIMULATED_PUBLIC_IPS)
    label = random.choice(LABELS)
    # 根据标签调整置信度范围，使数据更逼真
    confidence = round(random.uniform(0.70, 0.99), 4)
    return {
        "type": "classification",
        "data": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "src_ip": _random_ip(is_src=True),
            "dst_ip": dst_ip,
            "src_port": _random_port(is_server=False),
            "dst_port": _random_port(is_server=True),
            "protocol": random.choice(PROTOCOLS),
            "label": label,
            "confidence": confidence,
        },
    }


def _generate_statistics(start_time: float, total_bytes: int) -> dict:
    """生成一条模拟统计汇总"""
    elapsed = max(int(time.time() - start_time), 1)
    # 模拟总字节数持续增长
    new_bytes = total_bytes + random.randint(500_000, 5_000_000)
    current_rate = random.randint(100_000, 10_000_000)
    return {
        "type": "statistics",
        "data": {
            "total_bytes": new_bytes,
            "current_rate": current_rate,
            "duration_seconds": elapsed,
            "category_distribution": {
                "视频": random.randint(30, 50),
                "网页": random.randint(15, 30),
                "游戏": random.randint(10, 20),
                "会议": random.randint(3, 12),
                "下载": random.randint(2, 10),
                "音乐": random.randint(2, 8),
                "其他": random.randint(1, 5),
            },
        },
    }


class SocketManager:
    """
    WebSocket 连接管理与数据推送。
    使用 eventlet 绿色线程（或原生线程）定时向前端推送模拟数据。
    """

    def __init__(self):
        self._simulation_running = False
        self._simulation_thread = None
        self._start_time = 0.0
        self._total_bytes = 0

    def start_simulation(self, interface: str):
        """启动模拟数据生成线程"""
        if self._simulation_running:
            logger.warning("模拟已在运行中")
            return
        self._simulation_running = True
        self._start_time = time.time()
        self._total_bytes = 0
        # 使用 eventlet 绿色线程（兼容 SocketIO）
        self._simulation_thread = eventlet.spawn(self._simulation_loop)
        logger.info(f"[SocketManager] 模拟开始，网卡: {interface}")

    def stop_simulation(self):
        """停止模拟数据生成"""
        self._simulation_running = False
        if self._simulation_thread:
            eventlet.kill(self._simulation_thread)
            self._simulation_thread = None
        logger.info("[SocketManager] 模拟已停止")

    def _simulation_loop(self):
        """主循环：定时推送分类结果和统计汇总"""
        last_classification = 0
        last_statistics = 0
        while self._simulation_running:
            now = time.time()
            # 每 CLASSIFICATION_INTERVAL 秒推送一条分类结果
            if now - last_classification >= CLASSIFICATION_INTERVAL:
                msg = _generate_classification()
                emit("classification", msg, broadcast=True, namespace="/")
                last_classification = now
            # 每 STATISTICS_INTERVAL 秒推送一条统计汇总
            if now - last_statistics >= STATISTICS_INTERVAL:
                msg = _generate_statistics(self._start_time, self._total_bytes)
                self._total_bytes = msg["data"]["total_bytes"]
                emit("statistics", msg, broadcast=True, namespace="/")
                last_statistics = now
            eventlet.sleep(0.5)


# 全局单例
socket_manager = SocketManager()


class SmartTrafficNamespace(Namespace):
    """SocketIO 命名空间处理器"""

    def on_connect(self):
        client_id = request.sid
        logger.info(f"[SocketIO] 客户端连接: {client_id}")
        emit("welcome", {"message": "已连接到 SmartTraffic 服务器"}, room=client_id)

    def on_disconnect(self):
        client_id = request.sid
        logger.info(f"[SocketIO] 客户端断开: {client_id}")
