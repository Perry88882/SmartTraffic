"""
抓包管理器
通过 scapy 进行真实网络抓包；无管理员权限或无 Npcap 时用模拟模式。
"""

import ctypes
import logging
import platform
import queue
import threading
import time

logger = logging.getLogger(__name__)

_parser = None


def _get_parser():
    global _parser
    if _parser is None:
        from pipeline.packet_parser import parse_packet
        _parser = parse_packet
    return _parser


def _is_admin() -> bool:
    if platform.system() != "Windows":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _can_use_scapy() -> bool:
    """检查 scapy + Npcap 是否可用（不实际抓包，只检查导入和配置）"""
    try:
        from scapy.all import sniff
        from scapy.config import conf
        conf.use_pcap = True
        conf.use_npcap = True
        from scapy.interfaces import get_if_list
        ifaces = get_if_list()
        return len(ifaces) > 0
    except Exception:
        return False


class CaptureManager:
    """管理抓包生命周期"""

    def __init__(self, mode="auto", packet_queue_size=10000):
        self.interface = None
        self._running = False
        self._thread = None
        self._mode = "simulated"
        self.packet_queue = queue.Queue(maxsize=packet_queue_size)
        self._packet_count = 0

        # 检测真实抓包可行性
        if mode in ("auto", "real"):
            if _is_admin() and _can_use_scapy():
                self._mode = "real"
        if mode == "simulated":
            self._mode = "simulated"

    @property
    def mode(self):
        return self._mode

    @property
    def packet_count(self):
        return self._packet_count

    def start(self, interface: str):
        if self._running:
            return
        self.interface = interface
        self._running = True
        self._packet_count = 0
        self.packet_queue = queue.Queue(maxsize=self.packet_queue.maxsize)

        self._thread = threading.Thread(
            target=self._run, name="capture", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False

    @property
    def is_running(self):
        return self._running

    def _run(self):
        if self._mode == "real":
            try:
                self._capture_real()
            except Exception as e:
                logger.error(f"[Capture] 真实抓包失败: {e}")
                if self._running:
                    logger.info("[Capture] 降级为模拟模式")
                    self._mode = "simulated"
                    self._capture_simulated()
        else:
            logger.info("[Capture] 模拟模式")
            self._capture_simulated()

    def _capture_real(self):
        from scapy.all import sniff
        from scapy.config import conf
        from scapy.interfaces import resolve_iface
        conf.use_pcap = True
        conf.use_npcap = True

        iface = resolve_iface(self.interface)
        logger.info(f"[Capture] 真实抓包: {self.interface}")

        # 使用 timeout=1 确保即使没有包也能定期检查 _running 标志
        while self._running:
            sniff(
                iface=iface,
                prn=self._on_packet,
                timeout=1,
                store=False,
            )

    def _on_packet(self, pkt):
        if not self._running:
            return
        parsed = _get_parser()(pkt)
        if parsed is None:
            return
        self._packet_count += 1
        self._enqueue(parsed)

    def _capture_simulated(self):
        import random
        from datetime import datetime

        logger.info("[Capture] 模拟生成数据包")
        subnet = ["192.168.1.", "192.168.0.", "10.0.0.", "172.16.0."]
        pub_ip = ["8.8.8.8", "1.1.1.1", "223.5.5.5", "142.250.80.46"]
        protocols = ["TCP", "TCP", "TCP", "TCP", "UDP", "UDP"]
        ports = [443, 443, 80, 8080, 8443, 53, 22]

        while self._running:
            time.sleep(0.25)
            self._packet_count += 1
            self._enqueue({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "src_ip": random.choice(subnet) + str(random.randint(2, 254)),
                "dst_ip": random.choice(pub_ip),
                "src_port": random.randint(1024, 65535),
                "dst_port": random.choice(ports),
                "protocol": random.choice(protocols),
                "length": random.randint(60, 1500),
            })

    def _enqueue(self, pkt):
        try:
            self.packet_queue.put_nowait(pkt)
        except queue.Full:
            try:
                self.packet_queue.get_nowait()
                self.packet_queue.put_nowait(pkt)
            except queue.Empty:
                pass
