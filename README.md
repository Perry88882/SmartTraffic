# SmartTraffic — 智能网络流量分析系统

基于机器学习的网络流量实时分类与可视化系统，支持五层模型分析与安全风险评估。

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 后端语言 | Python | 3.10+ |
| Web 框架 | Flask + Flask-SocketIO | 3.x / 5.x |
| 异步引擎 | eventlet | 0.39+ |
| 抓包引擎 | scapy + Npcap | 2.4+ |
| 科学计算 | numpy, pandas | 2.x |
| 机器学习 | scikit-learn, joblib | 1.7+ |
| 数据库 | SQLite3（内置） | — |
| 前端框架 | React | 18.x |
| 构建工具 | Vite | 6.x |
| 图表库 | ECharts | 5.x |
| 通信协议 | Socket.IO | 4.x |

## 功能特性

**核心管道**
- **实时抓包** — Npcap + scapy 从物理网卡抓取原始数据包，支持 Ethernet 和 WiFi (802.11)，无管理员时自动降级为模拟模式
- **流重组** — 五元组（源/目的 IP、源/目的端口、协议）流表，按协议超时自动清理（TCP 60s / UDP 30s / ICMP 10s）
- **特征提取** — 每条流提取 30 维统计特征（包长分布、时间间隔、端口编码、协议标记等）
- **AI 分类** — 三级策略：RandomForest 模型推理 → 启发式规则 → 随机降级，支持 7 类应用识别

**五层模型分析**
- **物理层** — 包大小分布、速率时间线
- **数据链路层** — MAC 地址统计、帧类型分布（单播/广播/组播）
- **网络层** — IP 地址 Top10、TTL 分布、IPv4/IPv6、分片标志 DF/MF
- **传输层** — TCP/UDP 占比、端口热力图、TCP 标志位分布、窗口大小
- **应用层** — AI 分类分布、置信度、服务端口识别（HTTPS/DNS/SSH 等）

**AI 安全引擎**
- **IP 情报** — 内置 40+ 规则识别 Google、Cloudflare、Microsoft、Amazon、腾讯、阿里、字节跳动、百度等组织
- **GeoIP 定位** — 离线嵌入式数据库覆盖中国 20+ 省市 + 全球 60+ 国家/地区，IP → 城市 + 经纬度
- **风险评估** — 8 维度检测：端口风险、后门端口、协议异常、SYN 扫描、TTL 异常、横向移动、DNS 隧道、高危端点
- **四色等级** — 安全🟢 / 注意🟡 / 可疑🟠 / 高危🔴 + 0-100 评分

**UI/UX**
- **赛博朋克 HUD 风格** — 深空背景 + 网格线 + 扫描线动画
- **霓虹渐变配色** — 青 `#00e5ff` / 紫 `#a855f7` / 粉 `#ec4899`
- **毛玻璃控制栏** — backdrop-filter 模糊 + 底部发光边框
- **流畅动效** — 数据行滑入、详情面板弹入、卡片悬浮上浮、按钮发光扩散

**数据管理**
- **持久化存储** — SQLite 三表（capture_session / flow / classification）含索引，自动迁移
- **历史回查** — 日期筛选、按标签过滤、会话级五层聚合分析
- **记录删除** — 支持一键删除会话及关联数据
- **训练数据导出** — JSON 格式导出特征+标签用于模型训练

## 项目结构

```
SmartTraffic/
├── backend/
│   ├── app.py                          # Flask 入口 + SocketIO 启动
│   ├── config.py                       # 全局配置常量
│   ├── database.py                     # SQLite ORM + 自动迁移
│   ├── schema.sql                      # 数据库建表脚本
│   ├── train.py                        # 模型训练脚本
│   ├── api/
│   │   └── routes.py                   # REST API 路由
│   ├── websocket/
│   │   └── socket_handler.py           # WebSocket 事件 + 管道调度
│   ├── pipeline/
│   │   ├── capture_manager.py          # scapy 实时抓包管理（双模式）
│   │   ├── packet_parser.py            # 五层包解析器（Ethernet/WiFi）
│   │   ├── flow_reassembly.py          # 五元组流重组 + 超时清理
│   │   ├── feature_extractor.py        # 30维特征提取
│   │   ├── inference.py                # 三级分类推理
│   │   ├── security_analyzer.py        # AI 安全分析引擎
│   │   ├── session_analytics.py        # 会话五层聚合分析
│   │   └── geoip.py                    # 离线GeoIP物理地址识别
│   ├── models/
│   │   └── model.pkl                   # 训练好的分类模型
│   └── data/
│       └── smarttraffic.db             # SQLite 数据库文件
├── frontend/
│   └── src/
│       ├── main.jsx                    # ReactDOM 入口
│       ├── App.jsx                     # 根组件 + 状态管理
│       ├── components/
│       │   ├── ControlBar.jsx          # 网卡选择 + 启停 + 状态指示
│       │   ├── PieChart.jsx            # ECharts 类别分布饼图
│       │   ├── LineChart.jsx           # ECharts 识别趋势折线图
│       │   ├── RecordTable.jsx         # 实时记录表格 + 五层详情面板
│       │   └── HistoryModal.jsx        # 历史记录 + 五层分析 + 管理
│       ├── hooks/
│       │   └── useWebSocket.js         # SocketIO 连接封装
│       └── styles/
│           └── App.css                 # 深色仪表盘主题
├── docs/
│   ├── SmartTraffic项目设计报告.md
│   └── 团队协作指南.md
├── CHANGELOG.md                        # 版本记录
├── run.py                              # 一键启动脚本
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

访问 http://localhost:5173，选择网卡后点击「开始抓包」。

## 数据流

```
┌─────────────────────────────────────────────────────┐
│ scapy/Npcap 抓包 (Ethernet / WiFi 802.11)           │
│   │                                                 │
│   ▼                                                 │
│ packet_parser 五层解析 (MAC→IP→TCP/UDP→载荷)        │
│   │                                                 │
│   ▼                                                 │
│ flow_reassembly 流重组 (五元组 + 超时清理)          │
│   │                                                 │
│   ▼                                                 │
│ feature_extractor 30维特征向量                      │
│   │                                                 │
│   ▼                                                 │
│ inference 分类 (模型 → 启发式 → 随机)               │
│   │                                                 │
│   ├──→ security_analyzer 安全分析 (IP情报+风险评分) │
│   │                                                 │
│   ├──→ WebSocket 实时推送 (classification/statistics)│
│   └──→ SQLite 持久化                                │
└─────────────────────────────────────────────────────┘
```

## API 接口

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/cards` | 获取可用网卡列表（含 IP 地址） |
| GET | `/api/status` | 服务器状态（管理员/模式/原因/运行状态） |
| POST | `/api/start` | 开始抓包 `{"interface": "..."}` |
| POST | `/api/stop` | 停止抓包 |
| GET | `/api/history` | 查询分类记录（支持 `session_id`/`label`/`date_from`/`date_to` 筛选，分页） |
| GET | `/api/sessions` | 历史会话列表（支持日期筛选） |
| GET | `/api/sessions/<id>` | 会话详情 + 五层分析数据 |
| DELETE | `/api/sessions/<id>` | 删除会话及关联数据 |
| GET | `/api/dates` | 有数据的日期列表 |

## WebSocket 事件

| 事件 | 间隔 | 说明 |
|------|------|------|
| `classification` | 每 2s | 分类结果（含五层字段 + 安全分析 JSON） |
| `statistics` | 每 5s | 统计汇总（总流量、速率、包数、类别分布） |

## 训练模型

```bash
cd backend
python train.py --synthetic 5000          # 合成数据训练
python train.py --db --synthetic 3000     # 混合真实数据 + 合成数据
```

## 常见问题

| 现象 | 解决方案 |
|------|----------|
| 网卡列表为空 | 以管理员身份运行终端 |
| 显示"模拟模式" | 悬停标签查看原因；最常见是未以管理员运行 |
| WiFi 无法抓包 | 部分无线网卡驱动不支持 Npcap，尝试以太网 |
| 饼图全为 0 | 等待 5 秒，首次统计推送有延迟 |
| 端口 5000 被占用 | `netstat -ano \| findstr :5000` → `taskkill /PID XXX /F` |
| 折线图点太多 | 正常现象，累积计数线性增长 |

## 版本

| 版本 | 日期 | 要点 |
|------|------|------|
| **v1.2** | 2026-06-15 | GeoIP 物理地址识别、赛博朋克 HUD 重设计、前端性能优化 |
| v1.1 | 2026-05-13 | 五层模型分析、AI 安全引擎、历史记录管理 |
| v1.0 | 2026-05-13 | 完整管道集成、真实抓包、SQLite 持久化、WiFi 支持 |
| v0.1 | 2026-04-27 | 项目骨架，Flask + React + 模拟数据 |
