# SmartTraffic — 智能网络流量分析系统

基于机器学习的网络流量实时分类与可视化系统。

## 技术栈

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
| 通信协议 | Socket.IO | 4.x |

## 功能特性

- **实时抓包** — 基于 Npcap + scapy 从物理网卡抓取原始网络数据包，支持 Ethernet 和 WiFi (802.11)
- **流重组** — 按五元组（源/目的 IP、源/目的端口、协议）将离散数据包聚合为网络流，超时自动清理
- **特征提取** — 从每条流中提取 30 维统计特征向量（包长分布、时间间隔、协议标记等）
- **AI 分类** — 三级策略：RandomForest 模型推理 → 启发式规则 → 随机降级，支持 7 类应用识别（视频/游戏/网页/下载/会议/音乐/其他）
- **持久化存储** — SQLite 数据库存储抓包会话、网络流、分类记录，支持历史查询与训练数据导出
- **实时可视化** — Web 深色仪表盘：类别分布饼图、识别趋势折线图、最近记录表格、流量速率统计

## 项目结构

```
SmartTraffic/
├── backend/
│   ├── app.py                      # Flask 入口 + SocketIO 启动
│   ├── config.py                   # 全局配置常量
│   ├── database.py                 # SQLite 连接 + CRUD
│   ├── schema.sql                  # 数据库建表脚本
│   ├── train.py                    # 模型训练脚本
│   ├── api/
│   │   └── routes.py               # REST API 路由
│   ├── websocket/
│   │   └── socket_handler.py       # WebSocket 事件 + 数据管道调度
│   ├── pipeline/
│   │   ├── capture_manager.py      # scapy 实时抓包管理
│   │   ├── packet_parser.py        # 原始包 → 结构化数据（支持 Ethernet/WiFi）
│   │   ├── flow_reassembly.py      # 数据包 → 网络流重组
│   │   ├── feature_extractor.py    # 流 → 30维特征向量
│   │   └── inference.py            # 特征 → 分类结果
│   ├── models/
│   │   └── model.pkl               # 训练好的分类模型
│   └── data/
│       └── smarttraffic.db         # SQLite 数据库文件
├── frontend/
│   └── src/
│       ├── main.jsx                # ReactDOM 入口
│       ├── App.jsx                 # 根组件 + 状态管理
│       ├── components/
│       │   ├── ControlBar.jsx      # 网卡选择 + 启停 + 状态指示
│       │   ├── PieChart.jsx        # ECharts 类别分布饼图
│       │   ├── LineChart.jsx       # ECharts 识别趋势折线图
│       │   └── RecordTable.jsx     # 最近识别记录表格
│       ├── hooks/
│       │   └── useWebSocket.js     # SocketIO 连接封装
│       └── styles/
│           └── App.css             # 深色仪表盘主题
├── docs/
│   ├── SmartTraffic项目设计报告.md
│   └── 团队协作指南.md
├── run.py                          # 一键启动脚本
└── README.md
```

## 快速启动

### 前提条件

- Python 3.10+
- Node.js 18+
- Npcap（Windows 真实抓包必需）: https://npcap.com

### 1. 启动后端（需管理员权限以进行真实抓包）

```bash
cd backend
pip install -r requirements.txt
python app.py
```
后端运行在 http://localhost:5000

### 2. 启动前端（新终端）

```bash
cd frontend
npm install
npm run dev
```
前端运行在 http://localhost:5173

### 3. 打开浏览器

访问 http://localhost:5173，选择网卡后点击"开始抓包"。

## 数据流

```
scapy/Npcap 抓包 → packet_parser 解析 → flow_reassembly 流重组
    → feature_extractor 30维特征 → inference 分类
    → WebSocket 推送 + SQLite 持久化
```

## API 接口

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/cards` | 获取可用网卡列表 |
| GET | `/api/status` | 获取服务器状态（管理员/模式/运行状态） |
| POST | `/api/start` | 开始抓包 `{"interface": "..."}` |
| POST | `/api/stop` | 停止抓包 |
| GET | `/api/history` | 查询历史分类记录（支持分页和标签筛选） |

## WebSocket 事件

| 事件 | 间隔 | 说明 |
|------|------|------|
| `classification` | 每 2s | 最新分类结果（IP、端口、协议、标签、置信度） |
| `statistics` | 每 5s | 统计汇总（总流量、速率、包数、类别分布） |

## 训练模型

```bash
cd backend
python train.py --synthetic 5000    # 使用合成数据训练
python train.py --db --synthetic 3000  # 混合数据库真实数据 + 合成数据
```

## 常见问题

| 现象 | 解决方案 |
|------|----------|
| 网卡列表为空 | 以管理员身份运行终端 |
| WiFi 无法抓包 | 部分无线网卡驱动不支持 Npcap，尝试用以太网卡 |
| 饼图全为 0 | 等待 5 秒让统计事件推送 |
| 端口 5000 被占用 | `netstat -ano \| findstr :5000` → `taskkill /PID XXX /F` |

## 版本

- **v1.0** — 完整管道集成、真实抓包、SQLite 持久化、WiFi 802.11 支持、模型训练脚本
- **v0.1** — 项目骨架，Flask + React + 模拟数据
