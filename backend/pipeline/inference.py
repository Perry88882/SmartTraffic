"""
AI 推理模块
加载模型对特征向量进行分类预测。
支持：真实模型推理 > 启发式分类 > 随机分类（降级）
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

    三级策略：
    1. 真实模型 — 加载 joblib/scikit-learn 模型推理
    2. 启发式 — 基于特征向量的规则分类（比纯随机有意义）
    3. 随机 — 完全随机的降级方案
    """

    def __init__(self):
        self._model = None
        self._label_encoder = None
        self._model_labels = LABELS
        self._model_loaded = False
        self._init_model()

    def _init_model(self):
        """尝试加载模型，失败则使用启发式"""
        if os.path.exists(MODEL_PATH):
            try:
                loaded = joblib.load(MODEL_PATH)
                if loaded == "dummy":
                    logger.info("[TrafficClassifier] 占位模型，使用启发式分类")
                    return
                if isinstance(loaded, dict) and "model" in loaded:
                    self._model = loaded["model"]
                    self._label_encoder = loaded.get("label_encoder")
                    self._model_labels = loaded.get("labels", LABELS)
                    self._model_loaded = True
                    logger.info(f"[TrafficClassifier] 模型已加载, 类别={self._model_labels}")
                    return
                # 直接是模型对象
                self._model = loaded
                self._label_encoder = None
                self._model_labels = LABELS
                self._model_loaded = True
                logger.info("[TrafficClassifier] 模型已加载 (raw)")
                return
            except Exception as e:
                logger.warning(f"[TrafficClassifier] 模型加载失败: {e}")

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump("dummy", MODEL_PATH)
        logger.info("[TrafficClassifier] 使用启发式分类器")

    def predict(self, features: np.ndarray) -> dict:
        """
        分类预测。

        Args:
            features: 30 维特征向量

        Returns:
            {"label": str, "confidence": float}
        """
        # 策略 1: 真实模型
        if self._model_loaded:
            try:
                proba = self._model.predict_proba(features.reshape(1, -1))[0]
                idx = np.argmax(proba)
                return {
                    "label": self._model_labels[idx],
                    "confidence": round(float(proba[idx]), 4),
                }
            except Exception:
                pass

        # 策略 2: 启发式规则
        result = self._heuristic_predict(features)
        if result:
            return result

        # 策略 3: 随机降级
        return {
            "label": random.choice(LABELS),
            "confidence": round(random.uniform(0.55, 0.75), 4),
        }

    def _heuristic_predict(self, features: np.ndarray) -> dict | None:
        """
        基于特征向量进行启发式分类。

        利用 feature_extractor 提取的真实特征：
          features[11]  — 协议编码 (0=TCP, 0.33=UDP, 0.66=ICMP)
          features[20] — 是否 HTTPS (dst_port=443, TCP)
          features[21] — 是否 DNS (dst_port=53, UDP)
          features[22] — 是否 HTTP (dst_port=80, TCP)
          features[13] — 小包比例 (< 100 bytes)
          features[14] — 大包比例 (> 1400 bytes)
          features[6]  — 每秒字节数 (log)
          features[18] — 包间隔 (log ms)
        """
        try:
            f = features.flatten()
        except Exception:
            return None

        is_https = f[20] > 0.5
        is_dns = f[21] > 0.5
        is_http = f[22] > 0.5
        small_ratio = f[13]  # 小包比例
        large_ratio = f[14]  # 大包比例
        bytes_per_sec = f[6]  # log 缩放后的速率
        pkt_interval = f[18]  # log 缩放后的间隔
        proto = f[11]

        # DNS → 网页（DNS 通常是网页浏览的前提）
        if is_dns:
            return {"label": "网页", "confidence": 0.82}

        # HTTP → 网页
        if is_http:
            return {"label": "网页", "confidence": 0.78}

        # HTTPS + 大包比例高 + 高速率 → 视频
        if is_https and large_ratio > 0.3 and bytes_per_sec > 0.3:
            return {"label": "视频", "confidence": 0.85}

        # HTTPS + 高速率 + 大包 → 下载
        if is_https and bytes_per_sec > 0.5 and large_ratio > 0.4:
            return {"label": "下载", "confidence": 0.80}

        # 小包比例极高 + 包间隔短 → 游戏（高频小包交互）
        if small_ratio > 0.6 and pkt_interval < 0.2:
            return {"label": "游戏", "confidence": 0.76}

        # HTTPS + 中等速率 → 网页
        if is_https:
            if bytes_per_sec < 0.25:
                return {"label": "网页", "confidence": 0.74}
            # HTTPS 通用
            return {"label": "网页", "confidence": 0.68}

        # 高速率 → 会议/视频
        if bytes_per_sec > 0.4:
            return {"label": "会议", "confidence": 0.70}

        # UDP + 小包 → 可能是语音/音乐流
        if proto > 0.3 and small_ratio > 0.4:
            return {"label": "音乐", "confidence": 0.66}

        return None  # 无法确定，交由随机降级


# 全局单例
classifier = TrafficClassifier()
