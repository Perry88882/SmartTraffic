"""
数据包解析器
将 scapy 原始数据包解析为标准化 dict，供管道下游消费。
支持 Ethernet 和 WiFi (802.11) 帧。
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_packet(pkt) -> dict | None:
    """
    解析 scapy 数据包，提取关键字段。

    支持的链路层: Ethernet / WiFi (RadioTap + Dot11)
    支持的网络层: IP / IPv6
    支持的传输层: TCP / UDP / ICMP

    Returns:
        标准化 dict，包含 src_ip, dst_ip, src_port, dst_port, protocol, length, timestamp
        解析失败返回 None
    """
    try:
        from scapy.layers.inet import IP, IPv6, TCP, UDP, ICMP
        from scapy.layers.l2 import Ether
        from scapy.layers.dot11 import Dot11, RadioTap
    except ImportError:
        logger.debug("scapy 不可用，跳过数据包解析")
        return None

    if not pkt:
        return None

    ip_layer = None
    length = 0

    # ── 链路层判断 ──
    # 以太网帧
    if pkt.haslayer(Ether):
        ip_layer = pkt[IP] if pkt.haslayer(IP) else (pkt[IPv6] if pkt.haslayer(IPv6) else None)
        length = pkt[Ether].len if hasattr(pkt[Ether], 'len') else len(pkt)

    # WiFi 802.11 帧（可能包裹在 RadioTap 头里）
    elif pkt.haslayer(Dot11):
        # 尝试跨过 RadioTap 层
        target = pkt[RadioTap] if pkt.haslayer(RadioTap) else pkt
        dot11 = target[Dot11]

        # 只处理数据帧 (type=2)，忽略管理帧(0)和控制帧(1)
        if dot11.type != 2:
            return None

        ip_layer = target[IP] if target.haslayer(IP) else (target[IPv6] if target.haslayer(IPv6) else None)
        length = dot11.len if hasattr(dot11, 'len') and dot11.len else len(pkt)

    else:
        # 裸 IP 层（某些隧道/回环接口）
        if pkt.haslayer(IP):
            ip_layer = pkt[IP]
        elif pkt.haslayer(IPv6):
            ip_layer = pkt[IPv6]
        if ip_layer is None:
            return None
        length = ip_layer.len

    if ip_layer is None:
        return None

    src_ip = ip_layer.src
    dst_ip = ip_layer.dst
    length = ip_layer.len or length

    protocol = "OTHER"
    src_port = 0
    dst_port = 0

    if pkt.haslayer(TCP):
        protocol = "TCP"
        tcp = pkt[TCP]
        src_port = tcp.sport
        dst_port = tcp.dport
    elif pkt.haslayer(UDP):
        protocol = "UDP"
        udp = pkt[UDP]
        src_port = udp.sport
        dst_port = udp.dport
    elif pkt.haslayer(ICMP):
        protocol = "ICMP"

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "protocol": protocol,
        "length": length,
    }
