"""
特征提取模块
从 Flow 对象中提取真实统计特征向量供 ML 模型使用。
"""

import logging
import math
import time

import numpy as np

from config import FEATURE_VECTOR_SIZE

logger = logging.getLogger(__name__)

# 常见服务端口 → 应用类型映射（用于端口特征编码）
PORT_CATEGORY = {
    443: 1,   # HTTPS (Web/Video/Cloud)
    80: 2,    # HTTP (Web)
    8080: 3,  # HTTP-Alt
    8443: 4,  # HTTPS-Alt
    53: 5,    # DNS
    22: 6,    # SSH
    25: 7,    # SMTP
    110: 8,   # POP3
    143: 9,   # IMAP
    993: 10,  # IMAPS
    3389: 11, # RDP
    21: 12,   # FTP
    3306: 13, # MySQL
    5432: 14, # PostgreSQL
    27017: 15,# MongoDB
}


def extract_features(flow) -> np.ndarray:
    """
    从 Flow 对象中提取统计特征向量。

    特征维度（30 维）:
      0-1:  包计数、总字节数（log 缩放）
      2-3:  平均包大小、最大包大小（log 缩放）
      4:    包大小标准差 / 平均包大小（变异系数）
      5-6:  流持续时间、每秒字节数（log 缩放）
      7:    源端口（编码）
      8:    目的端口类别
      9-10: 第一个包/最后一个包大小
      11:   协议编码 (TCP=0, UDP=1, ICMP=2, 其他=3)
      12-20:保留位（供扩展）
      21-29:协议/端口组合特征
    """
    features = np.zeros(FEATURE_VECTOR_SIZE, dtype=np.float32)

    if flow is None or not flow.packets:
        return features

    packets = flow.packets
    pkt_count = len(packets)

    # ── 包长统计 ──
    sizes = np.array([p.get("length", 0) for p in packets], dtype=np.float32)
    total_bytes = float(flow.total_bytes)
    avg_size = np.mean(sizes) if len(sizes) > 0 else 0.0
    max_size = np.max(sizes) if len(sizes) > 0 else 0.0
    min_size = np.min(sizes) if len(sizes) > 0 else 0.0
    std_size = np.std(sizes) if len(sizes) > 0 else 0.0

    features[0] = _log1p(pkt_count, scale=50)
    features[1] = _log1p(total_bytes, scale=1e6)
    features[2] = _log1p(avg_size, scale=1500)
    features[3] = _log1p(max_size, scale=1500)

    # 变异系数：标准差/均值（若均值 > 0）
    features[4] = std_size / avg_size if avg_size > 1 else 0.0

    # ── 时间统计 ──
    now = time.time()
    start_time = getattr(flow, 'start_time', now - 1)
    last_seen = getattr(flow, 'last_seen', now)
    duration = max(last_seen - start_time, 0.001)  # 至少 1ms
    bytes_per_sec = total_bytes / duration if duration > 0 else 0.0

    features[5] = _log1p(duration, scale=60)
    features[6] = _log1p(bytes_per_sec, scale=1e6)

    # ── 端口特征 ──
    src_port = flow.src_port or 0
    dst_port = flow.dst_port or 0

    features[7] = _log1p(src_port, scale=65535)
    features[8] = PORT_CATEGORY.get(dst_port, 16) / 16.0  # 归一化到 [0,1]

    # ── 首尾包大小 ──
    first_size = sizes[0] if len(sizes) > 0 else 0
    last_size = sizes[-1] if len(sizes) > 0 else 0
    features[9] = _log1p(first_size, scale=1500)
    features[10] = _log1p(last_size, scale=1500)

    # ── 协议编码 ──
    proto_map = {"TCP": 0.0, "UDP": 0.33, "ICMP": 0.66}
    features[11] = proto_map.get(flow.protocol, 1.0)

    # ── 派生特征 (12-20) ──
    # 源/目的端口比率
    features[12] = _safe_ratio(dst_port, src_port)
    # 小包比例 (< 100 bytes)
    small_pkts = np.sum(sizes < 100)
    features[13] = small_pkts / pkt_count if pkt_count > 0 else 0.0
    # 大包比例 (> 1400 bytes)
    large_pkts = np.sum(sizes > 1400)
    features[14] = large_pkts / pkt_count if pkt_count > 0 else 0.0
    # 包大小跨度 (max - min) / max
    features[15] = (max_size - min_size) / max_size if max_size > 0 else 0.0
    # 是否是常见服务端口
    features[16] = 1.0 if dst_port in (443, 80, 53, 22, 8080, 8443) else 0.0
    # 源端口是否 > 1024（通常客户端端口）
    features[17] = 1.0 if src_port >= 1024 else 0.0
    # 每包平均间隔（秒）
    features[18] = _log1p(duration / pkt_count * 1000, scale=100) if pkt_count > 0 else 0.0
    # 总包数的对数
    features[19] = min(math.log2(pkt_count + 1) / 10.0, 1.0)

    # ── 协议+端口组合特征 (20-29) ──
    # 是否 HTTPS (443/TCP)
    features[20] = 1.0 if dst_port == 443 and flow.protocol == "TCP" else 0.0
    # 是否 DNS (53/UDP)
    features[21] = 1.0 if dst_port == 53 and flow.protocol == "UDP" else 0.0
    # 是否 HTTP (80/TCP)
    features[22] = 1.0 if dst_port == 80 and flow.protocol == "TCP" else 0.0
    # 剩余位补零（供训练真实模型时扩展）

    return features


def _log1p(value: float, scale: float = 1.0) -> float:
    """对数缩放，将大范围值映射到 [0, 1]"""
    if value <= 0:
        return 0.0
    scaled = np.log1p(value / scale)
    return float(np.clip(scaled, 0.0, 1.0))


def _safe_ratio(a: float, b: float, default: float = 0.0) -> float:
    """安全除法"""
    if b == 0:
        return default
    return float(np.clip(a / b, 0.0, 1.0))
