# SmartTraffic — 智能网络流量分析系统

基于机器学习的网络流量实时分类与可视化系统。

## 技术栈

- **后端**：Python 3.10 + Flask + Flask-SocketIO + eventlet + Flask-CORS
- **前端**：React 18 + Vite + ECharts + socket.io-client + axios
- **AI/ML**：scikit-learn（占位模拟推理）
- **抓包**：scapy（占位模块结构）

## 项目结构

```
SmartTraffic/
├── backend/
│   ├── app.py              # Flask 入口
│   ├── api/routes.py       # REST API 路由
│   ├── websocket/socket_handler.py  # WebSocket 推送
│   ├── pipeline/           # 数据处理流水线（占位）
│   ├── models/             # ML 模型文件
│   ├── config.py           # 全局配置
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # 主应用组件
│   │   ├── components/     # UI 组件
│   │   ├── hooks/          # 自定义 Hooks
│   │   └── styles/         # 样式文件
│   ├── package.json
│   └── vite.config.js
├── run.py                  # 一键启动脚本
└── README.md
```

## 快速启动

### 前提条件

- Python 3.10+
- Node.js 18+

### 1. 启动后端

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

访问 http://localhost:5173，选择网卡后点击"开始抓包"即可看到模拟数据。

## 使用说明

1. 页面打开后会自动连接到 WebSocket 服务器
2. 在下拉框中选择模拟网卡（eth0 / wlan0 / lo）
3. 点击 **开始抓包** 启动模拟数据生成
4. 每 2 秒收到一条分类结果，每 5 秒收到一次统计汇总
5. 饼图展示类别分布，折线图展示趋势，表格展示最近记录
