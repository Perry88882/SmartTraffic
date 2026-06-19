# SmartTraffic 智能网络流量分析系统 — 项目设计报告

---

## 一、项目设计总概

### 1.1 项目背景

随着互联网流量爆炸式增长，网络流量分类与识别在网络管理、QoS 保障、安全审计等领域具有重要意义。传统基于端口或深度包检测（DPI）的方法难以应对加密流量的挑战。本系统采用**机器学习方法**，通过提取网络流量的统计特征，实现对加密流量的实时应用分类（视频、游戏、网页、下载、会议、音乐等），并将数据持久化存储以供历史回查与模型迭代训练。

### 1.2 系统目标

| 目标 | 描述 |
|------|------|
| **实时抓包** | 基于 Npcap + scapy 从物理网卡抓取原始网络数据包 |
| **流重组** | 按五元组（源/目的 IP、源/目的端口、协议）将离散数据包聚合为网络流 |
| **特征提取** | 从每条流中提取 30 维统计特征向量（包长分布、时间间隔、协议标记等） |
| **AI 分类** | 启发式规则 + scikit-learn 模型进行应用类别识别 |
| **持久化存储** | SQLite 数据库存储抓包会话、网络流、分类记录 |
| **实时可视化** | Web 仪表盘展示分类结果、类别分布饼图、趋势折线图 |

### 1.3 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                     浏览器前端                            │
│     React 18 + Vite + ECharts + socket.io-client        │
│                  http://localhost:5173                   │
└────────────────────────┬─────────────────────────────────┘
                         │  HTTP REST  +  WebSocket
                         ▼
┌──────────────────────────────────────────────────────────┐
│                  Flask 后端服务器                         │
│     Flask + Flask-SocketIO + eventlet                    │
│                  http://localhost:5000                   │
│                                                          │
│  ┌───────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │ REST API  │  │ WebSocket │  │ 数据管道 (Pipeline) │  │
│  │ routes.py │  │ handler   │  │                    │  │
│  └───────────┘  └───────────┘  │ capture → parse    │  │
│                                │ → reassembly       │  │
│  ┌───────────┐                 │ → features         │  │
│  │  SQLite   │                 │ → inference        │  │
│  │  Database │                 └────────────────────┘  │
│  └───────────┘                                         │
└────────────────────────┬─────────────────────────────────┘
                         │  scapy + Npcap
                         ▼
┌──────────────────────────────────────────────────────────┐
│                  操作系统网络栈                           │
│              网卡 (WLAN / 以太网)                        │
└──────────────────────────────────────────────────────────┘
```

### 1.4 开发环境

| 类别 | 技术 | 版本 |
|------|------|------|
| 后端语言 | Python | 3.10+ |
| Web 框架 | Flask + Flask-SocketIO | 3.x / 5.x |
| 异步引擎 | eventlet | 0.39+ |
| 抓包引擎 | scapy + Npcap | 2.6+ |
| 科学计算 | numpy, pandas | 2.x |
| 机器学习 | scikit-learn, joblib | 1.7+ |
| 数据库 | SQLite3（内置） | — |
| 前端框架 | React | 18.x |
| 构建工具 | Vite | 6.x |
| 图表库 | ECharts | 5.x |
| 通信协议 | Socket.IO (Engine.IO v4) | 4.x |

---

## 二、项目模块划分

### 2.1 目录结构

```
SmartTraffic/
├── backend/                       ← Python 后端
│   ├── app.py                     ← [入口] Flask 工厂 + SocketIO 启动
│   ├── config.py                  ← [配置] 全局常量定义
│   ├── database.py                ← [数据库] SQLite 连接 + ORM
│   ├── api/
│   │   └── routes.py              ← [API层] RESTful 接口
│   ├── websocket/
│   │   └── socket_handler.py      ← [通信层] WebSocket 事件 + 数据推送
│   ├── pipeline/
│   │   ├── capture_manager.py     ← [采集层] scapy 实时抓包管理
│   │   ├── packet_parser.py       ← [解析层] 原始包 → 结构化数据
│   │   ├── flow_reassembly.py     ← [流重组] 数据包 → 网络流
│   │   ├── feature_extractor.py   ← [特征层] 流 → 30维特征向量
│   │   └── inference.py           ← [推理层] 特征 → 分类结果
│   └── models/
│       └── model.pkl              ← [模型] 训练好的 scikit-learn 模型
├── frontend/                      ← React 前端
│   └── src/
│       ├── main.jsx               ← [入口] ReactDOM 渲染
│       ├── App.jsx                ← [根组件] 状态管理 + 布局
│       ├── components/
│       │   ├── ControlBar.jsx     ← [控制栏] 网卡选择 + 启停
│       │   ├── PieChart.jsx       ← [饼图] 类别分布 ECharts
│       │   ├── LineChart.jsx      ← [折线图] 识别趋势 ECharts
│       │   └── RecordTable.jsx    ← [表格] 最近识别记录
│       ├── hooks/
│       │   └── useWebSocket.js    ← [Hook] SocketIO 连接封装
│       └── styles/
│           └── App.css            ← [样式] 深色仪表盘主题
└── docs/                          ← 文档
    └── SmartTraffic项目设计报告.md
```

### 2.2 模块职责详表

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| **app.py** | Flask 工厂模式创建应用；CORS 跨域配置；蓝图注册；SocketIO 启动 | 配置常量 | Flask app 实例 |
| **config.py** | 全局常量：协议超时、推送间隔、ML 参数、数据库路径 | — | 常量定义 |
| **database.py** | SQLite 连接管理；建表；CRUD 封装 | SQL 语句 | 查询结果 |
| **routes.py** | REST API：网卡列表 `/api/cards`、启停 `/api/start` `/api/stop`、历史查询 `/api/history` | HTTP 请求 | JSON 响应 |
| **socket_handler.py** | SocketIO 命名空间；后台任务调度；从 pipeline 接收分类结果推送到前端 | 启停信号 | WebSocket 事件 |
| **capture_manager.py** | scapy.sniff() 真实抓包；线程安全数据包队列；后台线程管理 | 网卡名称 | 数据包队列 (Queue) |
| **packet_parser.py** | 解析 scapy 原始包：提取 IP/TCP/UDP/ICMP 层字段 | scapy Packet | dict(IP, Port, Proto, Len, Time) |
| **flow_reassembly.py** | 五元组哈希流表；数据包聚合为 Flow 对象；超时流清理 | 数据包 dict | Flow 对象 |
| **feature_extractor.py** | 30 维统计特征：包长均值/方差、到达间隔、端口编码、协议标记 | Flow 对象 | 30维 numpy 向量 |
| **inference.py** | 加载 joblib 模型；特征→分类预测；启发式规则降级 | 特征向量 | {label, confidence} |
| **ControlBar.jsx** | 网卡下拉选择（从 API 获取）；启停按钮；连接状态指示灯 | 用户点击 | API 调用 |
| **PieChart.jsx** | ECharts 饼图：响应式渲染类别分布占比 | 分布对象 | SVG 图表 |
| **LineChart.jsx** | ECharts 折线图：按时间展示各类别累积识别趋势 | 记录数组 | SVG 图表 |
| **RecordTable.jsx** | 最近 10 条识别记录：时间、IP、端口、协议、分类、置信度 | 记录数组 | HTML 表格 |
| **useWebSocket.js** | SocketIO 客户端生命周期；自动重连；消息分发 | — | lastMessage, isConnected |
| **App.jsx** | 全局状态管理 (useState)；WebSocket 消息处理；布局编排 | WebSocket 消息 | 子组件 props |

---

## 三、模块间关系

### 3.1 完整数据流

```
┌────────────────────────────────────────────────────────────────────┐
│                          scapy 抓包层                              │
│                                                                   │
│  scapy.sniff(iface="WLAN", prn=callback)                          │
│      │                                                            │
│      │ 原始 Ethernet/IP/TCP 数据包                                 │
│      ▼                                                            │
│  ┌──────────────────┐                                             │
│  │ packet_parser.py │  提取: src_ip, dst_ip, src_port,            │
│  │   parse_packet() │        dst_port, protocol, length, timestamp│
│  └────────┬─────────┘                                             │
│           │ dict                                                   │
│           ▼                                                       │
│  ┌──────────────────┐                                             │
│  │flow_reassembly.py│  五元组哈希 → 流表                           │
│  │  process_packet()│  超时清理 (TCP 60s, UDP 30s)               │
│  └────────┬─────────┘                                             │
│           │ Flow 对象                                              │
│           ▼                                                       │
│  ┌──────────────────┐                                             │
│  │feature_extractor │  30 维特征向量:                              │
│  │ extract_features │  包长统计(6维) + 时间统计(3维)              │
│  │      .py         │  + 端口编码(2维) + 协议标记(1维)            │
│  └────────┬─────────┘  + 派生特征(8维) + 组合特征(10维)           │
│           │ numpy[30]                                              │
│           ▼                                                       │
│  ┌──────────────────┐                                             │
│  │  inference.py    │  joblib 模型 → label + confidence            │
│  │    predict()     │  无模型时启发式规则降级                       │
│  └────────┬─────────┘                                             │
│           │ {label, confidence}                                    │
└───────────┼───────────────────────────────────────────────────────┘
            │
            ├────────────────────────────┐
            ▼                            ▼
   ┌──────────────────┐        ┌──────────────────┐
   │  socket_handler  │        │   database.py    │
   │  emit("classifi- │        │   INSERT INTO    │
   │  cation", msg)   │        │   classification │
   └────────┬─────────┘        └──────────────────┘
            │ SocketIO
            ▼
   ┌──────────────────┐
   │  前端仪表盘       │
   │  PieChart 饼图   │
   │  LineChart 折线图 │
   │  RecordTable 表格 │
   └──────────────────┘
```

### 3.2 前后端通信协议

| 方向 | 方式 | 端点 | 触发时机 | 数据格式 |
|------|------|------|----------|----------|
| 前端→后端 | HTTP GET | `/api/cards` | 页面加载 | `{"interfaces": ["WLAN", "以太网", ...]}` |
| 前端→后端 | HTTP GET | `/api/status` | 页面加载 | `{"is_admin": true, "mode": "real", "is_running": false}` |
| 前端→后端 | HTTP POST | `/api/start` | 用户点击"开始抓包" | `{"interface": "WLAN"}` → `{"status": "started"}` |
| 前端→后端 | HTTP POST | `/api/stop` | 用户点击"停止抓包" | — → `{"status": "stopped"}` |
| 前端→后端 | HTTP GET | `/api/history` | 用户查看历史 | `{"records": [...], "total": 1500}` |
| 后端→前端 | SocketIO | `classification` | 每 2 秒 | `{"type":"classification","data":{"timestamp","src_ip","dst_ip","src_port","dst_port","protocol","label","confidence"}}` |
| 后端→前端 | SocketIO | `statistics` | 每 5 秒 | `{"type":"statistics","data":{"total_bytes","current_rate","total_packets","duration_seconds","category_distribution"}}` |

### 3.3 分类消息格式

```json
{
  "type": "classification",
  "data": {
    "timestamp": "2026-05-11 14:32:05.123",
    "src_ip": "192.168.1.105",
    "dst_ip": "142.250.80.46",
    "src_port": 49648,
    "dst_port": 443,
    "protocol": "TCP",
    "label": "网页",
    "confidence": 0.9214
  }
}
```

---

## 四、数据库设计

### 4.1 设计目标

系统需要对抓包过程中产生的**会话信息、网络流元数据、分类结果、原始特征向量**进行持久化存储。数据用于：

- 历史分类记录查询与回放
- 模型训练数据集构建
- 流量统计分析与报表
- 异常检测与审计

### 4.2 技术选型

| 方案 | 适用场景 |
|------|----------|
| SQLite3（当前） | 单机部署、MVP 阶段，零配置、嵌入式、Python 内置支持 |
| PostgreSQL（扩展） | 多用户、高并发生产环境，支持 JSON 字段、全文检索、时序查询 |

MVP 阶段使用 SQLite3，通过 Python 标准库 `sqlite3` 操作，数据库文件存储在 `backend/data/smarttraffic.db`。向上迁移到 PostgreSQL 仅需更换连接字符串。

### 4.3 ER 图

```
┌──────────────────────┐          ┌──────────────────────┐
│   CaptureSession     │          │       Flow           │
├──────────────────────┤          ├──────────────────────┤
│ PK id         INTEGER│ 1 ─── N │ PK id         INTEGER│
│    interface  TEXT   │          │ FK session_id INTEGER│
│    start_time TEXT   │          │    flow_id    TEXT   │
│    end_time   TEXT   │          │    src_ip     TEXT   │
│    total_pkts INTEGER│          │    dst_ip     TEXT   │
│    total_bytesINTEGER│          │    src_port   INTEGER│
│    status     TEXT   │          │    dst_port   INTEGER│
│    created_at TEXT   │          │    protocol   TEXT   │
└──────────────────────┘          │    pkt_count  INTEGER│
                                  │    total_bytesINTEGER│
                                  │    start_time REAL   │
                                  │    last_seen  REAL   │
                                  │    created_at TEXT   │
                                  └──────────┬───────────┘
                                             │ 1 ─── N
                                             ▼
                                  ┌──────────────────────┐
                                  │   Classification     │
                                  ├──────────────────────┤
                                  │ PK id         INTEGER│
                                  │ FK session_id INTEGER│
                                  │ FK flow_id    INTEGER│
                                  │    label       TEXT  │
                                  │    confidence  REAL  │
                                  │    features    TEXT  │  ← JSON 格式存储30维向量
                                  │    src_ip      TEXT  │
                                  │    dst_ip      TEXT  │
                                  │    src_port    INTEGER│
                                  │    dst_port    INTEGER│
                                  │    protocol    TEXT  │
                                  │    created_at  TEXT  │
                                  └──────────────────────┘
```

### 4.4 完整建表 SQL

```sql
-- ============================================================
-- SmartTraffic 数据库初始化脚本
-- 数据库: SQLite3
-- 路径: backend/data/smarttraffic.db
-- ============================================================

-- 抓包会话表
-- 每次"开始→停止"为一个会话，记录会话级别的统计信息
CREATE TABLE IF NOT EXISTS capture_session (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    interface       VARCHAR(100)  NOT NULL,              -- 抓包网卡 (WLAN, 以太网)
    start_time      DATETIME      NOT NULL,              -- 会话开始时间
    end_time        DATETIME,                            -- 会话结束时间（停止时回填）
    total_packets   INTEGER       DEFAULT 0,             -- 本会话总包数
    total_bytes     INTEGER       DEFAULT 0,             -- 本会话总字节数
    status          VARCHAR(20)   DEFAULT 'running',     -- running | stopped | error
    created_at      DATETIME      DEFAULT CURRENT_TIMESTAMP
);

-- 网络流表
-- 五元组唯一定义一条流，存储流的元数据
CREATE TABLE IF NOT EXISTS flow (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER       NOT NULL,              -- 所属会话
    flow_id         VARCHAR(200)  NOT NULL UNIQUE,       -- 五元组哈希标识
    src_ip          VARCHAR(45)   NOT NULL,
    dst_ip          VARCHAR(45)   NOT NULL,
    src_port        INTEGER,
    dst_port        INTEGER,
    protocol        VARCHAR(10),                         -- TCP | UDP | ICMP
    pkt_count       INTEGER       DEFAULT 0,             -- 流内数据包数
    total_bytes     INTEGER       DEFAULT 0,             -- 流内总字节数
    start_time      REAL,                                -- 流开始时间戳 (time.time())
    last_seen       REAL,                                -- 流最后活跃时间
    created_at      DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES capture_session(id)
);

-- 分类记录表
-- 每次对数据包运行推理后写入一条记录
CREATE TABLE IF NOT EXISTS classification (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER       NOT NULL,
    flow_id         INTEGER,                             -- 关联的网络流
    label           VARCHAR(20)   NOT NULL,              -- 分类标签 (视频/游戏/网页/...)
    confidence      REAL           NOT NULL,              -- 置信度 [0, 1]
    features        TEXT,                                -- 30维特征向量 JSON: [0.12, 0.45, ...]
    src_ip          VARCHAR(45)   NOT NULL,
    dst_ip          VARCHAR(45)   NOT NULL,
    src_port        INTEGER,
    dst_port        INTEGER,
    protocol        VARCHAR(10),
    created_at      DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES capture_session(id),
    FOREIGN KEY (flow_id)    REFERENCES flow(id)
);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_session_status    ON capture_session(status);
CREATE INDEX IF NOT EXISTS idx_session_time      ON capture_session(start_time);
CREATE INDEX IF NOT EXISTS idx_flow_session      ON flow(session_id);
CREATE INDEX IF NOT EXISTS idx_flow_5tuple       ON flow(src_ip, dst_ip, src_port, dst_port, protocol);
CREATE INDEX IF NOT EXISTS idx_cls_session       ON classification(session_id);
CREATE INDEX IF NOT EXISTS idx_cls_label         ON classification(label);
CREATE INDEX IF NOT EXISTS idx_cls_created       ON classification(created_at);
CREATE INDEX IF NOT EXISTS idx_cls_session_label ON classification(session_id, label);
```

### 4.5 Python 数据库模块设计

```python
# backend/database.py — 数据库操作封装

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "smarttraffic.db")


class Database:
    """SQLite 数据库管理器（单例）"""

    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """执行建表 SQL"""
        with open(os.path.join(os.path.dirname(__file__), "schema.sql")) as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    # --- 会话操作 ---
    def create_session(self, interface: str) -> int:
        ...

    def end_session(self, session_id: int, total_packets: int, total_bytes: int):
        ...

    # --- 流操作 ---
    def upsert_flow(self, session_id: int, flow) -> int:
        ...

    # --- 分类记录 ---
    def insert_classification(self, session_id, flow_id, label,
                               confidence, features, pkt) -> int:
        ...

    def query_history(self, session_id=None, label=None,
                      limit=100, offset=0) -> list[dict]:
        ...

    def get_statistics(self, session_id: int) -> dict:
        """返回某会话的统计: 各类别数量、总包数、字节数"""
        ...

    # --- 特征导出（用于模型训练） ---
    def export_training_data(self, limit=10000):
        """导出 features + label 用于训练新模型"""
        ...


# 全局单例
db = Database()
```

### 4.6 数据量估算

| 表 | 单次会话（10分钟） | 每日（8小时） | 保留策略 |
|----|-------------------|--------------|----------|
| capture_session | 1 行 | ~48 行 | 永久保留 |
| flow | ~500 行 | ~24,000 行 | 按月归档 |
| classification | ~300 行 (每2s一条) | ~14,400 行 | 按月归档 |

数据库文件预估大小：10MB/天（含特征向量 JSON），常规使用约 300MB/月。

---

## 五、小组详细分工安排

### 5.1 分工总表

| 模块 | 负责人 | 核心工作 | 难度 |
|------|--------|----------|------|
| 后端架构 + WebSocket + 数据库 | **蒲宇贤** | Flask 工厂、REST API、SocketIO 实时推送、SQLite 持久化 | ★★★★ |
| 数据管道（全链路） | **陈怡璇** | scapy 抓包、包解析、流重组、特征提取、推理分类 | ★★★★ |
| 前端仪表盘 | **罗薪** | React 组件、ECharts 图表、SocketIO 客户端、深色主题 | ★★★★ |
| 测试 + 文档 + 集成部署 | **黄思源** | 单元测试、联调测试、项目文档、演示 PPT、Git 管理 | ★★★ |

### 5.2 个人详细任务清单

**蒲宇贤 — 后端架构 + 数据持久化**

| # | 任务 | 涉及文件 |
|---|------|----------|
| A1 | Flask 工厂模式创建应用 + CORS 配置 + 蓝图注册 | `app.py` |
| A2 | 全局配置常量定义（超时、间隔、路径） | `config.py` |
| A3 | RESTful API 设计：`/api/cards` `/api/start` `/api/stop` `/api/status` `/api/history` | `api/routes.py` |
| A4 | SocketIO 命名空间注册、后台任务调度 | `websocket/socket_handler.py` |
| A5 | SQLite 建表 + Python 数据库封装 (CRUD) | `database.py`, `schema.sql` |
| A6 | 分类记录实时写入数据库 | `socket_handler.py` 中集成 |
| A7 | 历史记录查询接口 `/api/history` | `api/routes.py` |
| A8 | eventlet 异步服务器配置、前后端联调 | `app.py` |
| A9 | GitHub 仓库管理、代码合并 | — |

**陈怡璇 — 数据管道工程师**

| # | 任务 | 涉及文件 |
|---|------|----------|
| B1 | Npcap 环境配置、scapy 接口检测 | `capture_manager.py` |
| B2 | scapy.sniff() 实时抓包 + 线程安全数据包队列 | `capture_manager.py` |
| B3 | 原始包解析：IP/TCP/UDP/ICMP 字段提取 | `packet_parser.py` |
| B4 | 五元组流重组：哈希流表 + 超时清理 | `flow_reassembly.py` |
| B5 | 30 维统计特征提取：包长分布、时间间隔、端口编码、协议标记 | `feature_extractor.py` |
| B6 | 启发式分类规则 + joblib 模型加载 + 推理接口 | `inference.py` |
| B7 | 特征向量写入数据库（JSON 格式） | 与 A 协作 |
| B8 | 模型训练脚本（数据导出 → 特征标注 → 训练 → 保存 model.pkl） | `train.py` (新建) |

**罗薪 — 前端工程师**

| # | 任务 | 涉及文件 |
|---|------|----------|
| C1 | Vite 项目搭建 + React 根组件 + 深色主题 CSS | `main.jsx`, `App.css` |
| C2 | 控制栏组件：网卡下拉选择、启停按钮、模式标签、连接状态 | `ControlBar.jsx` |
| C3 | ECharts 饼图组件：响应式类别分布展示 | `PieChart.jsx` |
| C4 | ECharts 折线图组件：各类别累积识别趋势 | `LineChart.jsx` |
| C5 | 记录表格组件：最近 10 条记录、协议标记、置信度百分比 | `RecordTable.jsx` |
| C6 | SocketIO Hook：连接管理、自动重连、消息分发 | `useWebSocket.js` |
| C7 | Vite 代理配置（API + WebSocket） | `vite.config.js` |
| C8 | 全局状态管理 + 组件布局编排 | `App.jsx` |
| C9 | 历史记录页面 / 模态框 (扩展) | 新建组件 |

**黄思源 — 测试 + 文档 + 集成**

| # | 任务 | 涉及文件 |
|---|------|----------|
| D1 | 项目设计报告撰写 | `SmartTraffic项目设计报告.md` |
| D2 | README.md 编写（启动指南、架构图、技术栈） | `README.md` |
| D3 | 团队协作指南（Git 规范、环境搭建） | `docs/团队协作指南.md` |
| D4 | 后端单元测试：pytest 测试 API 接口 | `tests/test_api.py` |
| D5 | 后端单元测试：pytest 测试 pipeline 各模块 | `tests/test_pipeline.py` |
| D6 | 数据库 CRUD 测试 | `tests/test_database.py` |
| D7 | 前端组件测试（渲染测试、交互测试） | `tests/test_components.*` |
| D8 | 全链路集成测试：启动→抓包→分类→存储→查询 | `tests/test_integration.py` |
| D9 | 功能测试报告 + Bug 跟踪 | 文档 |
| D10 | 最终演示 PPT | `docs/SmartTraffic演示.pptx` |
| D11 | 代码 Review + Git 冲突协助 | — |

### 5.3 模块依赖关系

```
         ┌─────────────┐
         │ 蒲宇贤 (后端API) │
         └──────┬──────┘
                │ 定义接口规范
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│陈怡璇(管道)│  │罗薪(前端)│  │黄思源(测试)│
│          │  │          │  │          │
│ 提供     │  │ 消费     │  │ 验证     │
│ 数据     │  │ 数据     │  │ 全链路   │
└──────────┘  └──────────┘  └──────────┘
```

**协作时序：**

1. **A** 先完成 API 接口定义（路由 + 数据格式）→ 通知 B 和 C
2. **B** 按接口规范实现数据管道 → 通知 A 集成
3. **A** 集成管道 → 通知 C 联调
4. **C** 前端联调 SocketIO + API
5. **D** 全链路测试 → 发现问题 → A/B/C 修复 → D 回归测试
6. **D** 代码 Review + 合并 master + 撰写文档

---

## 六、实验注意事项

### 6.1 环境准备清单

| # | 事项 | 说明 |
|---|------|------|
| 1 | Python 3.10+ | 官方下载安装，勾选 "Add to PATH" |
| 2 | Node.js 18+ | LTS 版本，含 npm |
| 3 | Git | 代码版本管理 |
| 4 | Npcap | https://npcap.com 下载安装，勾选 "WinPcap API-compatible Mode" |
| 5 | pip 清华镜像 | `pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple` |
| 6 | npm 淘宝镜像 | `npm config set registry https://registry.npmmirror.com` |
| 7 | Git 身份配置 | `git config --global user.name "姓名"` / `git config --global user.email "邮箱"` |

### 6.2 启动顺序

> **必须先启动后端，再启动前端。** 真实抓包需管理员权限。

```bash
# ===== 终端 1：后端（右键 → 以管理员身份运行）=====
cd backend
pip install -r requirements.txt          # 首次运行
python app.py
# 日志输出: [SmartTraffic] http://0.0.0.0:5000

# ===== 终端 2：前端 =====
cd frontend
npm install                              # 首次运行
npm run dev
# 日志输出: http://localhost:5173
```

浏览器打开 `http://localhost:5173`，选择已连接网卡（如 WLAN），点击"开始抓包"。

### 6.3 常见问题排查

| 现象 | 原因 | 解决方案 |
|------|------|----------|
| pip install 超时 | 默认 PyPI 源慢 | 切换清华镜像 |
| npm install 卡住 | npm 源慢 | 切换 npmmirror 镜像 |
| 后端启动报 `Address already in use` | 5000 端口被占用 | `netstat -ano \| findstr :5000` → `taskkill /PID XXX /F` |
| 前端页面空白 | 后端离线 | 确认 `python app.py` 在运行 |
| WebSocket 连不上 | 后端未启动 / CORS 配置问题 | 检查后端日志，确认 `[SocketIO] 客户端连接` 出现 |
| 抓包无数据 / 网卡列表为空 | 未以管理员身份运行 | 右键终端 → 以管理员身份运行 → 重新 `python app.py` |
| 图表不显示 | ECharts 初始化异常 | F12 Console 查看报错 |
| 饼图全为 0 | 数据未到达（首次推送需等 5 秒） | 等待统计事件推送 |
| 按钮点击卡住 | API 调用超时 | 刷新页面，确认后端无报错 |
| 数据库文件未生成 | `backend/data/` 目录权限 | 确认有写入权限 |

### 6.4 安全警告

- **不要抓取非本人设备流量**：scapy 开启混杂模式可捕获局域网内其他设备流量，可能涉及法律风险
- **模型文件不入库**：`backend/models/model.pkl` 已在 `.gitignore` 中排除
- **生产部署时关闭 DEBUG**：`config.py` 中 `DEBUG = False`
- **生产部署时收紧 CORS**：限制为实际域名，不要使用 `*`

---

## 七、小组任务清单

### 7.1 第一阶段：环境搭建（第 1 周）

| # | 任务 | 负责人 | 状态 |
|---|------|--------|------|
| 1 | 安装 Python 3.10+ | 全员 | ☐ |
| 2 | 安装 Node.js 18+ | 全员 | ☐ |
| 3 | 安装 Npcap | 全员 | ☐ |
| 4 | Git 克隆仓库 + 配置身份 | 全员 | ☐ |
| 5 | 配置 pip/npm 国内镜像 | 全员 | ☐ |
| 6 | `pip install -r requirements.txt` | 全员 | ☐ |
| 7 | `npm install` | 全员 | ☐ |
| 8 | 启动后端验证端口 5000 | A | ☐ |
| 9 | 启动前端验证端口 5173 | C | ☐ |
| 10 | 验证 WebSocket 连接成功 | C、D | ☐ |

### 7.2 第二阶段：核心功能开发（第 2-3 周）

| # | 任务 | 负责人 | 状态 |
|---|------|--------|------|
| 11 | Flask 工厂 + CORS + 蓝图注册 | A | ☐ |
| 12 | REST API 全部接口实现 | A | ☐ |
| 13 | SQLite 建表 + database.py CRUD 封装 | A | ☐ |
| 14 | SocketIO 事件处理 + 后台任务 | A | ☐ |
| 15 | 分类/统计消息实时写入数据库 | A | ☐ |
| 16 | scapy 抓包管理 + 线程安全队列 | B | ☐ |
| 17 | 数据包解析器 (IP/TCP/UDP/ICMP) | B | ☐ |
| 18 | 五元组流重组 + 超时清理 | B | ☐ |
| 19 | 30维统计特征提取 | B | ☐ |
| 20 | 启发式分类 + joblib 模型接口 | B | ☐ |
| 21 | 控制栏 + ECharts 饼图组件 | C | ☐ |
| 22 | ECharts 折线图 + 记录表格组件 | C | ☐ |
| 23 | SocketIO Hook + 前后端联调 | C | ☐ |
| 24 | 深色仪表盘 CSS + 响应式布局 | C | ☐ |

### 7.3 第三阶段：数据库与持久化（第 3 周）

| # | 任务 | 负责人 | 状态 |
|---|------|--------|------|
| 25 | 分类记录实时写入验证 | A、B | ☐ |
| 26 | 历史记录查询接口 + 前端展示 | A、C | ☐ |
| 27 | 数据库导出功能（JSON/CSV） | A | ☐ |
| 28 | 训练数据导出脚本 | B | ☐ |
| 29 | 数据库性能测试（1万条写入） | D | ☐ |

### 7.4 第四阶段：测试与交付（第 3-4 周）

| # | 任务 | 负责人 | 状态 |
|---|------|--------|------|
| 30 | API 接口单元测试 (pytest) | D | ☐ |
| 31 | Pipeline 模块单元测试 | D | ☐ |
| 32 | 数据库 CRUD 测试 | D | ☐ |
| 33 | 全链路集成测试 | D | ☐ |
| 34 | 启停循环测试（连续 10 次） | D | ☐ |
| 35 | 抓包 + 存储 + 查询全流程验证 | D | ☐ |
| 36 | 功能测试报告 + Bug 清单 | D | ☐ |
| 37 | 代码 Review + 合并 master | D | ☐ |
| 38 | 项目设计报告定稿 | D | ☐ |
| 39 | README.md 最终版 | D | ☐ |
| 40 | 演示 PPT 制作 | D | ☐ |
| 41 | 答辩演练 | 全员 | ☐ |
| 42 | 最终代码推送 + 交付物提交 | A | ☐ |

### 状态标记

| 符号 | 含义 |
|------|------|
| ☐ | 未开始 |
| ◐ | 进行中 |
| ☑ | 已完成 |
| ⚠ | 有阻塞 |

---

## 附录 A：特征向量维度定义

| 维度 | 特征 | 计算方法 |
|------|------|----------|
| 0 | 包计数 (log) | `log1p(pkt_count / 50)` |
| 1 | 总字节数 (log) | `log1p(total_bytes / 1e6)` |
| 2 | 平均包大小 (log) | `log1p(avg_size / 1500)` |
| 3 | 最大包大小 (log) | `log1p(max_size / 1500)` |
| 4 | 包大小变异系数 | `std_size / avg_size` |
| 5 | 流持续时间 (log) | `log1p(duration / 60)` |
| 6 | 每秒字节数 (log) | `log1p(bytes_per_sec / 1e6)` |
| 7 | 源端口编码 (log) | `log1p(src_port / 65535)` |
| 8 | 目的端口类别 | 常见端口映射 / 16 |
| 9-10 | 首/尾包大小 | `log1p(size / 1500)` |
| 11 | 协议编码 | TCP=0, UDP=0.33, ICMP=0.66 |
| 12 | 端口比率 | `dst_port / src_port` |
| 13 | 小包比例 | `< 100 bytes 占比` |
| 14 | 大包比例 | `> 1400 bytes 占比` |
| 15 | 包长跨度 | `(max - min) / max` |
| 16 | 常见服务端口标记 | 443/80/53/22 为 1 |
| 17 | 客户端端口标记 | src_port >= 1024 为 1 |
| 18 | 每包平均间隔 (log) | `log1p(interval_ms / 100)` |
| 19 | 总包数 (log2) | `log2(pkt_count + 1) / 10` |
| 20 | 是否 HTTPS | 443/TCP 为 1 |
| 21 | 是否 DNS | 53/UDP 为 1 |
| 22 | 是否 HTTP | 80/TCP 为 1 |
| 23-29 | 保留扩展位 | 当前填 0，供训练模型使用 |

---

## 附录 B：数据库 ER 图（文字简化版）

```
CaptureSession (会话)
    id ──────────────┐
    interface        │ 1:N
    start_time       │
    end_time         │
    total_packets    │
    total_bytes      │
    status           │
                     │
Flow (网络流)        │
    id ──────────────┤
    session_id ──────┘
    flow_id ─────────┐
    src_ip           │ 1:N
    dst_ip           │
    src_port         │
    dst_port         │
    protocol         │
    pkt_count        │
    total_bytes      │
    start_time       │
    last_seen        │
                     │
Classification (分类) │
    id               │
    session_id ──────┤ (冗余，加速查询)
    flow_id ─────────┘
    label            ← 目标变量 (视频/游戏/网页/...)
    confidence       ← 模型置信度 [0, 1]
    features         ← 30维特征向量 (JSON)
    src_ip
    dst_ip
    src_port
    dst_port
    protocol
    created_at
```

---

*文档版本：v1.0 | 日期：2026-05-11 | SmartTraffic 团队*
