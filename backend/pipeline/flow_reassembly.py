"""
流重组模块（占位）
将离散数据包按五元组（src_ip, dst_ip, src_port, dst_port, protocol）重组成 Flow。
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Flow:
    """表示一条网络流的抽象"""
    flow_id: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    packets: list = field(default_factory=list)
    total_bytes: int = 0
    start_time: Optional[float] = None
    last_seen: Optional[float] = None


class FlowReassembler:
    """
    维护流表，将收到的数据包分配到对应的 Flow。
    当前为占位实现，返回模拟 Flow 对象。
    """

    def __init__(self):
        self.flow_table: dict[str, Flow] = {}

    def process_packet(self, packet: dict) -> Flow:
        """
        处理一个数据包，返回其所属的 Flow 对象。

        Args:
            packet: 模拟的包字典，包含 src_ip, dst_ip 等字段

        Returns:
            Flow 对象
        """
        flow_id = self._compute_flow_id(packet)
        if flow_id not in self.flow_table:
            import time
            flow = Flow(
                flow_id=flow_id,
                src_ip=packet["src_ip"],
                dst_ip=packet["dst_ip"],
                src_port=packet["src_port"],
                dst_port=packet["dst_port"],
                protocol=packet["protocol"],
                start_time=time.time(),
            )
            self.flow_table[flow_id] = flow
            logger.debug(f"[FlowReassembler] 新建流: {flow_id}")
        flow = self.flow_table[flow_id]
        flow.packets.append(packet)
        flow.total_bytes += packet.get("length", 0)
        import time
        flow.last_seen = time.time()
        return flow

    def _compute_flow_id(self, packet: dict) -> str:
        """根据五元组计算流 ID"""
        return (
            f"{packet.get('src_ip')}:{packet.get('src_port')}"
            f"-{packet.get('dst_ip')}:{packet.get('dst_port')}"
            f"-{packet.get('protocol')}"
        )
