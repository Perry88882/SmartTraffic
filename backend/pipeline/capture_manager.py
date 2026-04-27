"""
抓包管理器（占位模块）
负责启动/停止网络抓包，真实场景中使用 scapy sniff。
"""

import logging
import threading

logger = logging.getLogger(__name__)


class CaptureManager:
    """
    管理网络抓包的生命周期。
    在真实环境中，内部使用 scapy.sniff() 抓取数据包；
    当前为占位实现，仅打印日志。
    """

    def __init__(self):
        self.interface = None
        self._running = False
        self._thread = None

    def start(self, interface: str):
        """在指定网卡上启动抓包"""
        if self._running:
            logger.warning(f"抓包已在 {self.interface} 上运行，忽略重复启动")
            return
        self.interface = interface
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop, name="capture-thread", daemon=True
        )
        self._thread.start()
        logger.info(f"[CaptureManager] 开始在 {interface} 上抓包")

    def stop(self):
        """停止抓包"""
        if not self._running:
            logger.warning("抓包未在运行，无需停止")
            return
        self._running = False
        logger.info(f"[CaptureManager] 停止在 {self.interface} 上的抓包")

    @property
    def is_running(self) -> bool:
        return self._running

    def _capture_loop(self):
        """
        抓包主循环（占位）。
        真实场景中，此线程会调用 scapy.sniff(prn=self._on_packet, ...)
        """
        import time
        while self._running:
            # 模拟不断收到数据包
            time.sleep(0.5)
            logger.debug("[CaptureManager] 模拟接收数据包...")
