"""
安全分析引擎 — IP 情报 + 流量目的 + 风险评估
无外部 API 依赖，基于内置规则和启发式分析。
"""
import ipaddress
import logging

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# IP → 组织/服务 映射数据库
# ═══════════════════════════════════════════════════════════
IP_INTEL = [
    # Google
    (("8.8.8.8", "8.8.4.4"), "Google Public DNS", "DNS服务"),
    (("142.250.0.0/15",), "Google (YouTube/Gmail)", "视频/邮件/搜索"),
    (("172.217.0.0/16",), "Google Services", "搜索/云服务"),
    (("216.58.192.0/19",), "Google Global", "搜索/API"),
    (("34.0.0.0/8",), "Google Cloud", "云计算平台"),
    # Cloudflare
    (("1.1.1.1", "1.0.0.1"), "Cloudflare DNS", "DNS服务"),
    (("104.16.0.0/12",), "Cloudflare CDN", "CDN/安全代理"),
    # Microsoft
    (("13.64.0.0/11", "13.96.0.0/13", "13.104.0.0/14"), "Microsoft Azure", "云计算"),
    (("52.96.0.0/12",), "Microsoft 365 / Teams", "办公协作"),
    (("20.0.0.0/11",), "Microsoft Services", "云服务"),
    # Amazon
    (("18.0.0.0/8",), "Amazon AWS (美国)", "云计算"),
    (("52.0.0.0/8",), "Amazon AWS / CloudFront", "云计算/CDN"),
    (("54.0.0.0/8",), "Amazon AWS", "云计算"),
    (("35.0.0.0/8",), "Amazon AWS", "云计算"),
    # Meta
    (("31.13.0.0/16",), "Facebook / Instagram", "社交网络"),
    (("157.240.0.0/16",), "Facebook CDN", "社交/CDN"),
    # Apple
    (("17.0.0.0/8",), "Apple Services", "推送/icloud"),
    # Twitter/X
    (("104.244.42.0/24", "199.16.156.0/22"), "Twitter / X", "社交网络"),
    # 国内互联网
    (("183.0.0.0/10", "120.0.0.0/10"), "腾讯 (QQ/微信/游戏)", "即时通讯/游戏"),
    (("110.0.0.0/8",), "阿里云/淘宝", "电商/云计算"),
    (("47.0.0.0/8",), "阿里云 CDN", "CDN/云计算"),
    (("180.76.0.0/16", "103.235.46.0/24"), "百度", "搜索/AI"),
    (("123.0.0.0/8",), "中国电信 CDN", "CDN/宽带"),
    (("223.5.5.5", "223.6.6.6"), "阿里 DNS", "DNS服务"),
    (("180.101.50.242", "180.101.50.188"), "百度 CDN", "CDN"),
    (("39.156.66.0/24",), "字节跳动 (抖音/头条)", "短视频/信息流"),
    (("182.61.200.0/24", "182.61.0.0/16"), "百度云", "云计算"),
    (("203.205.0.0/16",), "腾讯云 CDN", "CDN/云服务"),
    (("119.0.0.0/8",), "中国联通/电信", "宽带运营商"),
    # CDN / 通用
    (("151.101.0.0/16",), "Fastly CDN", "CDN"),
    (("23.0.0.0/8",), "Akamai CDN", "CDN"),
    (("185.0.0.0/8",), "欧洲 CDN / 云", "CDN/云"),
    # GitHub / Git
    (("140.82.112.0/20",), "GitHub", "代码托管"),
    (("192.30.252.0/22",), "GitHub API", "代码托管"),
    # 本地/内网
    (("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"), "本地局域网", "内部网络"),
    (("169.254.0.0/16",), "APIPA 自动配置", "本地自分配"),
    (("127.0.0.0/8",), "Loopback 回环", "本机"),
]

# ═══════════════════════════════════════════════════════════
# 端口风险评分
# ═══════════════════════════════════════════════════════════
HIGH_RISK_PORTS = {
    22: ("SSH", 20, "远程管理 — 如非授权运维则为高危"),
    23: ("Telnet", 40, "明文远程登录 — 过时且不安全"),
    25: ("SMTP", 15, "邮件发送 — 可能是垃圾邮件僵尸"),
    135: ("RPC", 35, "Windows RPC — 常被蠕虫利用"),
    139: ("NetBIOS", 30, "文件共享 — 勒索软件传播渠道"),
    445: ("SMB", 40, "Windows 文件共享 — 永恒之蓝漏洞"),
    1433: ("MSSQL", 25, "数据库 — 可能被爆破"),
    1521: ("Oracle", 25, "数据库 — 可能被爆破"),
    3306: ("MySQL", 25, "数据库 — 可能被爆破"),
    3389: ("RDP", 35, "远程桌面 — 常见爆破目标"),
    4444: ("Metasploit", 50, "知名渗透工具默认端口"),
    5555: ("ADB", 30, "Android Debug Bridge — 可能被远程控制"),
    6379: ("Redis", 25, "缓存 — 未授权访问风险"),
    6666: ("IRC/恶意", 40, "IRC 僵尸网络控制"),
    6667: ("IRC", 35, "IRC — 僵尸网络常用"),
    8080: ("HTTP-Alt", 5, "非标准 Web — 可能是管理面板"),
    8443: ("HTTPS-Alt", 5, "非标准 HTTPS"),
    8888: ("HTTP-Alt", 10, "代理或管理面板"),
    9999: ("后门", 45, "多个木马家族默认端口"),
    27017: ("MongoDB", 30, "NoSQL — 曾大规模未授权访问"),
    31337: ("BackOrifice", 55, "经典后门程序默认端口"),
    49152: ("Windows RPC", 20, "高端口 RPC — 异常"),
}

COMMON_SAFE_PORTS = {80, 443, 53, 8080, 8443, 993, 465, 587, 143, 110}
SAFE_NETWORKS = {"10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8"}


class TrafficAnalysis:
    """单次流量分析结果"""
    def __init__(self):
        self.src_org = "未知"
        self.dst_org = "未知"
        self.src_service = "未知"
        self.dst_service = "未知"
        self.purpose = "数据传输"
        self.risk_score = 0
        self.risk_level = "安全"
        self.risk_reasons = []
        self.suspicious = False
        self.notes = ""


def _match_ip(ip_str: str) -> tuple[str, str]:
    """匹配 IP 到组织和用途"""
    if not ip_str:
        return "未知", "未知"
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return "未知", "未知"

    # 检查本地网络
    for net_str in SAFE_NETWORKS:
        if ip in ipaddress.ip_network(net_str):
            return "本地网络", "内部通信"

    # 匹配已知服务
    for nets, org, service in IP_INTEL:
        for net_str in nets:
            try:
                if "/" in net_str:
                    if ip in ipaddress.ip_network(net_str):
                        return org, service
                else:
                    if ip == ipaddress.ip_address(net_str):
                        return org, service
            except ValueError:
                continue

    return "未知 (公网)", "一般互联网流量"


def analyze_traffic(parsed: dict, features, label: str, confidence: float) -> TrafficAnalysis:
    """
    综合分析一条流量记录。

    Args:
        parsed: 解析后的包 dict (含 MAC、IP、端口、TTL等五层信息)
        features: 30维特征向量
        label: AI 分类标签
        confidence: 分类置信度

    Returns:
        TrafficAnalysis 对象
    """
    a = TrafficAnalysis()
    src_ip = parsed.get("src_ip", "")
    dst_ip = parsed.get("dst_ip", "")
    dst_port = parsed.get("dst_port", 0)
    src_port = parsed.get("src_port", 0)
    protocol = parsed.get("protocol", "OTHER")
    tcp_flags = parsed.get("tcp_flags", "")
    ttl = parsed.get("ttl", 0)
    payload_size = parsed.get("payload_size", 0)
    window_size = parsed.get("window_size", 0)

    # ── IP 情报 ──
    a.src_org, a.src_service = _match_ip(src_ip)
    a.dst_org, a.dst_service = _match_ip(dst_ip)

    # ── 流量目的分析 ──
    purpose_parts = []
    if dst_port == 443 and protocol == "TCP":
        purpose_parts.append("HTTPS 加密通信")
        if "Google" in a.dst_org or "Cloudflare" in a.dst_org:
            purpose_parts.append("(网页浏览/API调用)")
        elif "腾讯" in a.dst_org:
            purpose_parts.append("(微信/QQ/游戏)")
        elif "字节" in a.dst_org:
            purpose_parts.append("(抖音/头条)")
    elif dst_port == 80:
        purpose_parts.append("HTTP 明文通信")
    elif dst_port == 53:
        purpose_parts.append("DNS 域名解析")
    elif dst_port == 22:
        purpose_parts.append("SSH 远程管理")
    elif dst_port == 3389:
        purpose_parts.append("RDP 远程桌面")
    elif dst_port in (25, 587, 465):
        purpose_parts.append("邮件传输 (SMTP)")
    elif dst_port in (110, 143, 993):
        purpose_parts.append("邮件收取 (POP3/IMAP)")
    elif dst_port == 21:
        purpose_parts.append("FTP 文件传输")
    elif dst_port in (3306, 1433, 1521, 5432, 27017):
        purpose_parts.append("数据库访问")
    elif protocol == "UDP":
        purpose_parts.append("UDP 实时通信")
        if dst_port in (3478, 3479, 19302, 19303):
            purpose_parts.append("(WebRTC/视频会议)")
        elif dst_port in range(16384, 32768):
            purpose_parts.append("(VoIP/音视频流)")
    elif protocol == "ICMP":
        purpose_parts.append("ICMP 网络探测/诊断")

    if label == "视频":
        purpose_parts.append("→ 流媒体视频播放")
    elif label == "游戏":
        purpose_parts.append("→ 在线游戏数据传输")
    elif label == "网页":
        purpose_parts.append("→ 网页浏览")
    elif label == "下载":
        purpose_parts.append("→ 文件下载/更新")
    elif label == "会议":
        purpose_parts.append("→ 远程会议/视频通话")
    elif label == "音乐":
        purpose_parts.append("→ 音频流媒体")
    elif label == "其他":
        purpose_parts.append("→ 其他应用流量")

    a.purpose = " ".join(purpose_parts) if purpose_parts else "未知目的"

    # ── 风险评估 ──
    risk = 0
    reasons = []

    # 1. 端口检查
    if dst_port in HIGH_RISK_PORTS:
        name, port_risk, detail = HIGH_RISK_PORTS[dst_port]
        risk += port_risk
        reasons.append(f"端口 {dst_port} ({name}): {detail}")

    # 2. 高端口连接（动态端口范围外）
    if dst_port > 49152 and dst_port not in COMMON_SAFE_PORTS:
        risk += 10
        reasons.append(f"高端口 {dst_port}: 可能的后门通信端口")

    # 3. 协议异常
    if protocol == "ICMP" and payload_size > 100:
        risk += 20
        reasons.append(f"ICMP 大载荷 ({payload_size}B): 疑似隧道/数据外泄")

    if protocol == "UDP" and dst_port == 53 and payload_size > 512:
        risk += 15
        reasons.append(f"DNS 大包 ({payload_size}B): 疑似 DNS 隧道")

    # 4. TCP 标志位风险
    if tcp_flags and "SYN" in tcp_flags and "ACK" not in tcp_flags:
        if src_port > 60000:
            risk += 5
            reasons.append("SYN 扫描特征: 高端口 SYN 包")

    # 5. TTL 异常
    if ttl and ttl < 30:
        risk += 5
        reasons.append(f"低 TTL ({ttl}): 可能经过隧道/代理")

    # 6. 窗口大小异常
    if window_size and window_size > 65535:
        risk += 5
        reasons.append(f"异常窗口大小 ({window_size}): 可能的协议异常")

    # 7. 已知恶意模式
    if a.dst_org == "未知 (公网)" and dst_port in (4444, 31337, 6666, 6667, 9999):
        risk += 30
        reasons.append(f"高危: {a.dst_org} + 知名后门端口 {dst_port}")

    # 8. 内网横向移动检测
    if "本地网络" in a.src_org and "本地网络" in a.dst_org:
        if dst_port in (445, 135, 139, 3389, 22, 5985, 5986):
            risk += 15
            reasons.append("内网横向移动特征: 内网到内网的管理端口访问")

    # 确认风险等级
    a.risk_score = min(100, risk)

    if a.risk_score >= 50:
        a.risk_level = "高危"
        a.suspicious = True
    elif a.risk_score >= 25:
        a.risk_level = "可疑"
        a.suspicious = True
    elif a.risk_score >= 10:
        a.risk_level = "注意"
        a.suspicious = False
    else:
        a.risk_level = "安全"
        a.suspicious = False

    a.risk_reasons = reasons

    # ── 综合备注 ──
    notes_parts = []
    if a.dst_org not in ("未知", "未知 (公网)", "本地网络"):
        notes_parts.append(f"目标: {a.dst_org} ({a.dst_service})")
    if a.suspicious:
        notes_parts.append(f"风险: {a.risk_level} (评分 {a.risk_score})")
    else:
        notes_parts.append(f"安全 (评分 {a.risk_score})")
    a.notes = " | ".join(notes_parts) if notes_parts else "一般流量"

    return a
