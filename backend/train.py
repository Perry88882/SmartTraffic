"""
模型训练脚本
从数据库导出训练数据 → 训练 RandomForest → 保存 model.pkl

用法:
    python train.py                     # 从数据库导出数据训练
    python train.py --synthetic 5000    # 生成合成数据训练（无数据库时）
    python train.py --db --synthetic 3000  # 混合训练
"""
import argparse
import logging
import os
import sys

import joblib
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LABELS, MODEL_PATH

os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)


def generate_synthetic_data(n_samples: int) -> tuple[np.ndarray, np.ndarray]:
    """生成合成训练数据，基于启发式特征分布"""
    logger.info(f"生成 {n_samples} 条合成训练数据...")
    rng = np.random.default_rng(42)

    X_list, y_list = [], []

    patterns = [
        # (label, feature_template, probability)
        # 视频: HTTPS, 大包比例高, 高速率
        ("视频", lambda: {
            0: rng.uniform(0.3, 0.8), 1: rng.uniform(0.5, 0.9),
            2: rng.uniform(0.4, 0.7), 3: rng.uniform(0.5, 0.9),
            4: rng.uniform(0.1, 0.4), 5: rng.uniform(0.3, 0.8),
            6: rng.uniform(0.3, 0.7), 7: rng.uniform(0.2, 0.6),
            8: rng.uniform(0.0, 0.3), 9: rng.uniform(0.3, 0.8),
            10: rng.uniform(0.3, 0.8), 11: 0.0,
            12: rng.uniform(0.0, 0.3), 13: rng.uniform(0.0, 0.2),
            14: rng.uniform(0.3, 0.8), 15: rng.uniform(0.2, 0.6),
            16: 1.0, 17: 1.0, 18: rng.uniform(0.1, 0.4),
            19: rng.uniform(0.2, 0.5), 20: 1.0,
            21: 0.0, 22: 0.0,
        }),
        # 游戏: 小包比例高, 高频交互, UDP居多
        ("游戏", lambda: {
            0: rng.uniform(0.4, 0.9), 1: rng.uniform(0.1, 0.3),
            2: rng.uniform(0.1, 0.3), 3: rng.uniform(0.1, 0.3),
            4: rng.uniform(0.0, 0.2), 5: rng.uniform(0.5, 0.9),
            6: rng.uniform(0.1, 0.3), 7: rng.uniform(0.3, 0.7),
            8: rng.uniform(0.0, 0.4), 9: rng.uniform(0.0, 0.2),
            10: rng.uniform(0.0, 0.2), 11: rng.choice([0.0, 0.33]),
            12: rng.uniform(0.0, 0.3), 13: rng.uniform(0.5, 0.9),
            14: rng.uniform(0.0, 0.1), 15: rng.uniform(0.0, 0.3),
            16: rng.uniform(0.0, 0.5), 17: 1.0, 18: rng.uniform(0.0, 0.15),
            19: rng.uniform(0.3, 0.6), 20: rng.uniform(0.0, 0.3),
            21: rng.uniform(0.0, 0.3), 22: 0.0,
        }),
        # 网页: HTTP/HTTPS, 中等速率, 小/大包混合
        ("网页", lambda: {
            0: rng.uniform(0.1, 0.5), 1: rng.uniform(0.1, 0.5),
            2: rng.uniform(0.2, 0.5), 3: rng.uniform(0.3, 0.7),
            4: rng.uniform(0.1, 0.5), 5: rng.uniform(0.1, 0.5),
            6: rng.uniform(0.1, 0.3), 7: rng.uniform(0.2, 0.6),
            8: rng.uniform(0.0, 0.3), 9: rng.uniform(0.1, 0.5),
            10: rng.uniform(0.1, 0.5), 11: 0.0,
            12: rng.uniform(0.0, 0.3), 13: rng.uniform(0.1, 0.4),
            14: rng.uniform(0.1, 0.4), 15: rng.uniform(0.2, 0.6),
            16: rng.uniform(0.5, 1.0), 17: 1.0, 18: rng.uniform(0.1, 0.5),
            19: rng.uniform(0.1, 0.3), 20: rng.uniform(0.5, 1.0),
            21: 0.0, 22: rng.uniform(0.0, 0.5),
        }),
        # 下载: HTTPS, 超大包比例, 极高速率
        ("下载", lambda: {
            0: rng.uniform(0.2, 0.6), 1: rng.uniform(0.6, 1.0),
            2: rng.uniform(0.5, 0.9), 3: rng.uniform(0.6, 1.0),
            4: rng.uniform(0.0, 0.2), 5: rng.uniform(0.3, 0.8),
            6: rng.uniform(0.5, 0.9), 7: rng.uniform(0.2, 0.6),
            8: rng.uniform(0.0, 0.3), 9: rng.uniform(0.5, 0.9),
            10: rng.uniform(0.5, 0.9), 11: 0.0,
            12: rng.uniform(0.0, 0.2), 13: rng.uniform(0.0, 0.1),
            14: rng.uniform(0.5, 0.9), 15: rng.uniform(0.1, 0.3),
            16: 1.0, 17: 1.0, 18: rng.uniform(0.1, 0.4),
            19: rng.uniform(0.2, 0.5), 20: 1.0,
            21: 0.0, 22: 0.0,
        }),
        # 会议: UDP/TCP, 中等速率, 稳定包大小
        ("会议", lambda: {
            0: rng.uniform(0.2, 0.6), 1: rng.uniform(0.3, 0.7),
            2: rng.uniform(0.2, 0.5), 3: rng.uniform(0.3, 0.6),
            4: rng.uniform(0.0, 0.2), 5: rng.uniform(0.3, 0.8),
            6: rng.uniform(0.2, 0.5), 7: rng.uniform(0.2, 0.6),
            8: rng.uniform(0.0, 0.4), 9: rng.uniform(0.2, 0.5),
            10: rng.uniform(0.2, 0.5), 11: rng.choice([0.0, 0.33]),
            12: rng.uniform(0.0, 0.3), 13: rng.uniform(0.0, 0.2),
            14: rng.uniform(0.1, 0.4), 15: rng.uniform(0.1, 0.3),
            16: rng.uniform(0.0, 0.5), 17: 1.0, 18: rng.uniform(0.1, 0.3),
            19: rng.uniform(0.2, 0.5), 20: rng.uniform(0.0, 0.5),
            21: rng.uniform(0.0, 0.3), 22: 0.0,
        }),
        # 音乐: UDP, 小包, 低速率
        ("音乐", lambda: {
            0: rng.uniform(0.2, 0.6), 1: rng.uniform(0.1, 0.3),
            2: rng.uniform(0.1, 0.3), 3: rng.uniform(0.1, 0.3),
            4: rng.uniform(0.0, 0.2), 5: rng.uniform(0.3, 0.8),
            6: rng.uniform(0.0, 0.2), 7: rng.uniform(0.2, 0.6),
            8: rng.uniform(0.0, 0.4), 9: rng.uniform(0.0, 0.2),
            10: rng.uniform(0.0, 0.2), 11: 0.33,
            12: rng.uniform(0.0, 0.3), 13: rng.uniform(0.3, 0.7),
            14: rng.uniform(0.0, 0.1), 15: rng.uniform(0.0, 0.3),
            16: rng.uniform(0.0, 0.3), 17: 1.0, 18: rng.uniform(0.1, 0.4),
            19: rng.uniform(0.1, 0.3), 20: 0.0,
            21: rng.uniform(0.0, 0.3), 22: 0.0,
        }),
        # 其他: 混合特征
        ("其他", lambda: {
            0: rng.uniform(0.0, 0.4), 1: rng.uniform(0.0, 0.4),
            2: rng.uniform(0.1, 0.5), 3: rng.uniform(0.2, 0.6),
            4: rng.uniform(0.2, 0.6), 5: rng.uniform(0.1, 0.5),
            6: rng.uniform(0.0, 0.3), 7: rng.uniform(0.0, 1.0),
            8: rng.uniform(0.0, 1.0), 9: rng.uniform(0.0, 0.5),
            10: rng.uniform(0.0, 0.5), 11: rng.uniform(0.0, 1.0),
            12: rng.uniform(0.0, 0.5), 13: rng.uniform(0.0, 0.5),
            14: rng.uniform(0.0, 0.5), 15: rng.uniform(0.0, 0.7),
            16: rng.uniform(0.0, 0.5), 17: rng.uniform(0.0, 1.0), 18: rng.uniform(0.0, 0.5),
            19: rng.uniform(0.0, 0.3), 20: rng.uniform(0.0, 0.5),
            21: rng.uniform(0.0, 0.5), 22: rng.uniform(0.0, 0.5),
        }),
    ]

    samples_per_label = n_samples // len(patterns)
    for label, template_fn in patterns:
        for _ in range(samples_per_label):
            feats = np.zeros(30, dtype=np.float32)
            template = template_fn()
            for idx, val in template.items():
                feats[idx] = val
            # 在模板值上加少量噪声
            noise = rng.normal(0, 0.03, 30).astype(np.float32)
            feats += noise
            feats = np.clip(feats, 0.0, 1.0)
            # 填充保留位
            for i in range(23, 30):
                feats[i] = rng.uniform(0.0, 0.1)
            X_list.append(feats)
            y_list.append(label)

    return np.array(X_list), np.array(y_list)


def train_model(X: np.ndarray, y: np.ndarray):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.preprocessing import LabelEncoder

    logger.info(f"训练数据: X={X.shape}, y={y.shape}")
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    logger.info(f"类别: {le.classes_.tolist()}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)

    try:
        cv_scores = cross_val_score(model, X, y_enc, cv=5)
        cv_mean = cv_scores.mean()
    except Exception:
        cv_mean = None

    logger.info(f"训练集准确率: {train_acc:.4f}")
    logger.info(f"测试集准确率: {test_acc:.4f}")
    if cv_mean is not None:
        logger.info(f"5折交叉验证: {cv_mean:.4f} (+/- {cv_scores.std():.4f})")

    # 包装模型，保存时附带 LabelEncoder
    model_wrapper = {
        "model": model,
        "label_encoder": le,
        "feature_size": 30,
        "labels": le.classes_.tolist(),
    }

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model_wrapper, MODEL_PATH)
    logger.info(f"模型已保存至: {MODEL_PATH}")

    return model_wrapper


def load_data_from_db(limit: int = 10000):
    from database import db
    X, y = db.export_training_data(limit=limit)
    if X.size == 0:
        logger.warning("数据库中没有训练数据")
        return None, None
    return X, y


def main():
    parser = argparse.ArgumentParser(description="SmartTraffic 模型训练")
    parser.add_argument("--synthetic", type=int, default=0,
                        help="合成数据样本数（默认 0，不使用合成数据）")
    parser.add_argument("--db", action="store_true",
                        help="从数据库导出真实数据（可与 --synthetic 混合）")
    parser.add_argument("--db-limit", type=int, default=10000,
                        help="数据库导出上限")
    args = parser.parse_args()

    X_all, y_all = [], []

    if args.db:
        X_db, y_db = load_data_from_db(limit=args.db_limit)
        if X_db is not None and X_db.size > 0:
            X_all.append(X_db)
            y_all.append(y_db)

    if args.synthetic > 0:
        X_syn, y_syn = generate_synthetic_data(args.synthetic)
        X_all.append(X_syn)
        y_all.append(y_syn)

    if not X_all:
        logger.info("无数据源，使用默认 5000 条合成数据训练...")
        X_syn, y_syn = generate_synthetic_data(5000)
        X_all.append(X_syn)
        y_all.append(y_syn)

    X = np.vstack(X_all)
    y = np.concatenate(y_all)
    train_model(X, y)


if __name__ == "__main__":
    main()
