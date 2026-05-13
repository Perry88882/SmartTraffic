"""
数据包解析器 — 五层模型提取
将 scapy 原始数据包解析为标准化 dict，含完整 5 层信息。
支持 Ethernet 和 WiFi (802.11) 帧。
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _compute_frame_type(mac: str) -> str:
    """根据 MAC 地址判断帧类型"""
    if not mac or len(mac) < 17:
        return "unknown"
    first = mac[1] if mac[0] == '0' else mac[0] + mac[1]
    try:
        byte = int(first, 16)
        if byte & 1:         # 组播位
            return "broadcast" if mac.lower() == "ff:ff:ff:ff:ff:ff" else "multicast"
        return "unicast"
    except (ValueError, IndexError):
        return "unknown"


def _tcp_flags_str(flags_val) -> str:
    """TCP flags 数值 → 缩写字符串"""
    if not flags_val:
        return ""
    names = ["FIN", "SYN", "RST", "PSH", "ACK", "URG", "ECE", "CWR"]
    parts = []
    for i, name in enumerate(names):
        if flags_val & (1 << i):
            parts.append(name)
    return "/".join(parts) if parts else ""


def parse_packet(pkt) -> dict | None:
    """
    解析 scapy 数据包，提取 5 层关键字段。

    返回 dict 字段:
        链路层: src_mac, dst_mac, frame_type
        网络层: src_ip, dst_ip, ttl, ip_version, ip_flags
        传输层: src_port, dst_port, protocol, tcp_flags, window_size
        应用层: length (总长), payload_size
        元数据:   timestamp
    """
    try:
        from scapy.layers.inet import IP, TCP, UDP, ICMP
        from scapy.layers.l2 import Ether
    except ImportError:
        logger.debug("scapy 不可用，跳过数据包解析")
        return None

    IPv6 = None
    try:
        from scapy.layers.inet import IPv6
    except ImportError:
        try:
            from scapy.layers.inet6 import IPv6
        except ImportError:
            pass

    Dot11 = RadioTap = None
    try:
        from scapy.layers.dot11 import Dot11, RadioTap
    except ImportError:
        pass

    if not pkt:
        return None

    # ── 初始化所有字段 ──
    src_mac = dst_mac = ""
    frame_type = "unknown"
    src_ip = dst_ip = ""
    ttl = 0
    ip_version = 0
    ip_flags = ""
    src_port = dst_port = 0
    protocol = "OTHER"
    tcp_flags_str = ""
    window_size = 0
    total_len = len(pkt)
    payload_size = 0

    ip_layer = None
    transport_layer = None

    # ═══════════════════════════════════════════
    # 第 1-2 层: 物理层 & 数据链路层
    # ═══════════════════════════════════════════
    if pkt.haslayer(Ether):
        ether = pkt[Ether]
        src_mac = ether.src or ""
        dst_mac = ether.dst or ""
        frame_type = _compute_frame_type(dst_mac)
        ip_layer = pkt[IP] if pkt.haslayer(IP) else (pkt[IPv6] if IPv6 is not None and pkt.haslayer(IPv6) else None)
    elif Dot11 is not None and pkt.haslayer(Dot11):
        target = pkt[RadioTap] if RadioTap is not None and pkt.haslayer(RadioTap) else pkt
        dot11 = target[Dot11]
        src_mac = dot11.addr2 or ""
        dst_mac = dot11.addr1 or ""
        frame_type = _compute_frame_type(dst_mac)
        if dot11.type != 2:
            return None
        ip_layer = target[IP] if target.haslayer(IP) else (target[IPv6] if IPv6 is not None and target.haslayer(IPv6) else None)
    else:
        if pkt.haslayer(IP):
            ip_layer = pkt[IP]
        elif IPv6 is not None and pkt.haslayer(IPv6):
            ip_layer = pkt[IPv6]
        if ip_layer is None:
            return None

    if ip_layer is None:
        return None

    # ═══════════════════════════════════════════
    # 第 3 层: 网络层
    # ═══════════════════════════════════════════
    src_ip = ip_layer.src
    dst_ip = ip_layer.dst
    ttl = getattr(ip_layer, 'ttl', 0)
    ip_version = ip_layer.version if hasattr(ip_layer, 'version') else 4
    frag = getattr(ip_layer, 'flags', 0)
    ip_flags = []
    if frag & 2:
        ip_flags.append("DF")
    if frag & 1:
        ip_flags.append("MF")
    ip_flags = ",".join(ip_flags) if ip_flags else ""

    # ═══════════════════════════════════════════
    # 第 4 层: 传输层
    # ═══════════════════════════════════════════
    if pkt.haslayer(TCP):
        protocol = "TCP"
        tcp = pkt[TCP]
        src_port = tcp.sport
        dst_port = tcp.dport
        transport_layer = tcp
        tcp_flags_str = _tcp_flags_str(getattr(tcp, 'flags', 0))
        window_size = getattr(tcp, 'window', 0)
    elif pkt.haslayer(UDP):
        protocol = "UDP"
        udp = pkt[UDP]
        src_port = udp.sport
        dst_port = udp.dport
        transport_layer = udp
        window_size = getattr(udp, 'len', 0)
    elif pkt.haslayer(ICMP):
        protocol = "ICMP"
        icmp = pkt[ICMP]
        transport_layer = icmp

    # ═══════════════════════════════════════════
    # 第 5 层: 应用层（载荷）
    # ═══════════════════════════════════════════
    ip_header_len = getattr(ip_layer, 'ihl', 5) * 4 if hasattr(ip_layer, 'ihl') else 20
    transport_header_len = 0
    if protocol == "TCP":
        transport_header_len = getattr(transport_layer, 'dataofs', 5) * 4 if transport_layer else 20
    elif protocol == "UDP":
        transport_header_len = 8
    elif protocol == "ICMP":
        transport_header_len = 8

    ip_total = ip_layer.len or total_len
    payload_size = max(0, ip_total - ip_header_len - transport_header_len)

    return {
        # 数据链路层
        "src_mac": src_mac,
        "dst_mac": dst_mac,
        "frame_type": frame_type,
        # 网络层
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "ttl": ttl,
        "ip_version": ip_version,
        "ip_flags": ip_flags,
        # 传输层
        "src_port": src_port,
        "dst_port": dst_port,
        "protocol": protocol,
        "tcp_flags": tcp_flags_str,
        "window_size": window_size,
        # 应用层
        "length": ip_total,
        "payload_size": payload_size,
        # 元数据
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
    }
