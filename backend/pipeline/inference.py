"""
AI 推理模块（占位）
加载模型并对特征向量进行分类预测。
"""

import logging
import os
import random

import joblib
import numpy as np

from config import LABELS, MODEL_PATH

logger = logging.getLogger(__name__)


class TrafficClassifier:
    """
    网络流量分类器。
    在真实场景中加载训练好的 scikit-learn / PyTorch 模型；
    当前使用随机预测作为占位。
    """

    def __init__(self):
        self._model = None
        self._init_model()

    def _init_model(self):
        """初始化模型：若 model.pkl 存在则加载，否则创建占位模型文件"""
        if os.path.exists(MODEL_PATH):
            try:
                self._model = joblib.load(MODEL_PATH)
                logger.info(f"[TrafficClassifier] 已加载模型: {MODEL_PATH}")
                return
            except Exception as e:
                logger.warning(f"[TrafficClassifier] 模型加载失败: {e}，使用占位模式")

        # 创建占位模型文件
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump("dummy", MODEL_PATH)
        logger.info(f"[TrafficClassifier] 已创建占位模型文件: {MODEL_PATH}")

    def predict(self, features: np.ndarray) -> dict:
        """
        对特征向量进行分类预测。

        Args:
            features: 特征向量 (numpy array)

        Returns:
            包含 label 和 confidence 的字典
        """
        if self._model and self._model != "dummy":
            # 真实模型推理（占位）
            pass

        # 随机模拟分类结果
        label = random.choice(LABELS)
        confidence = round(random.uniform(0.65, 0.99), 4)
        return {"label": label, "confidence": confidence}


# 全局单例
classifier = TrafficClassifier()
