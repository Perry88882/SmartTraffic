"""
特征提取模块（占位）
从 Flow 对象中提取机器学习特征向量。
"""

import numpy as np

from config import FEATURE_VECTOR_SIZE


def extract_features(flow) -> np.ndarray:
    """
    从一条 Flow 中提取特征向量。

    在真实场景中，会计算：
        - 包长统计（均值、方差、最大/最小）
        - 到达时间间隔统计
        - 协议标志位比例（SYN/ACK/FIN/RST）
        - 端口信息编码
        - TLS 握手特征（SNI、证书长度等）
        - 有效载荷熵值

    Args:
        flow: Flow 对象

    Returns:
        长度为 FEATURE_VECTOR_SIZE 的 numpy 浮点数组
    """
    # 占位：返回随机特征向量，模拟真实的特征分布
    features = np.random.rand(FEATURE_VECTOR_SIZE).astype(np.float32)
    return features
