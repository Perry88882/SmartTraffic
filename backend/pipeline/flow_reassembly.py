"""
流重组模块
将离散数据包按五元组（src_ip, dst_ip, src_port, dst_port, protocol）重组成 Flow。
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# 协议超时（秒）
TIMEOUTS = {"TCP": 60, "UDP": 30, "ICMP": 10}


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
    """维护流表，将收到的数据包分配到对应的 Flow。"""

    def __init__(self):
        self.flow_table: dict[str, Flow] = {}
        self._last_cleanup = time.time()

    def process_packet(self, packet: dict) -> Flow:
        """
        处理一个数据包，返回其所属的 Flow 对象。
        """
        flow_id = self._compute_flow_id(packet)
        now = time.time()

        if flow_id not in self.flow_table:
            flow = Flow(
                flow_id=flow_id,
                src_ip=packet["src_ip"],
                dst_ip=packet["dst_ip"],
                src_port=packet["src_port"],
                dst_port=packet["dst_port"],
                protocol=packet["protocol"],
                start_time=now,
            )
            self.flow_table[flow_id] = flow
            logger.debug(f"[FlowReassembler] 新建流: {flow_id}")

        flow = self.flow_table[flow_id]
        flow.packets.append(packet)
        flow.total_bytes += packet.get("length", 0)
        flow.last_seen = now
        return flow

    def cleanup_stale_flows(self) -> int:
        """清理超时的流，返回清理数量"""
        now = time.time()
        stale = []
        for flow_id, flow in self.flow_table.items():
            timeout = TIMEOUTS.get(flow.protocol, 30)
            if flow.last_seen and (now - flow.last_seen) > timeout:
                stale.append(flow_id)

        for flow_id in stale:
            flow = self.flow_table.pop(flow_id)
            logger.debug(
                f"[FlowReassembler] 清理过期流: {flow_id}, "
                f"包数={len(flow.packets)}, 字节={flow.total_bytes}"
            )

        self._last_cleanup = now
        return len(stale)

    @property
    def flow_count(self) -> int:
        return len(self.flow_table)

    def _compute_flow_id(self, packet: dict) -> str:
        """根据五元组计算流 ID"""
        return (
            f"{packet.get('src_ip')}:{packet.get('src_port')}"
            f"-{packet.get('dst_ip')}:{packet.get('dst_port')}"
            f"-{packet.get('protocol')}"
        )
