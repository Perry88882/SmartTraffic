"""SmartTraffic 全局配置常量"""

import os

# Flask 配置
SECRET_KEY = os.environ.get("SECRET_KEY", "smarttraffic-secret-key-2026")
DEBUG = True

# 协议超时配置（秒）
TCP_TIMEOUT = 60
UDP_TIMEOUT = 30
ICMP_TIMEOUT = 10

# 流表清理间隔（秒）
FLOW_CLEANUP_INTERVAL = 30

# 抓包模式: "auto" 自动检测, "real" 强制真实, "simulated" 强制模拟
CAPTURE_MODE = "auto"
PACKET_QUEUE_SIZE = 10000
DEFAULT_SNAPLEN = 65535
DEFAULT_PROMISC = False

# WebSocket 推送间隔（秒）
CLASSIFICATION_INTERVAL = 2
STATISTICS_INTERVAL = 5

# ML 模型配置
FEATURE_VECTOR_SIZE = 30
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "model.pkl")
LABELS = ["视频", "游戏", "网页", "下载", "会议", "音乐", "其他"]

# 模拟流量网段
SIMULATED_SUBNETS = [
    "192.168.1.",
    "192.168.0.",
    "10.0.0.",
    "172.16.0.",
]
SIMULATED_PUBLIC_IPS = [
    "8.8.8.8",
    "1.1.1.1",
    "223.5.5.5",
    "180.101.50.242",
    "39.156.66.10",
    "142.250.80.46",
]

# CORS
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
