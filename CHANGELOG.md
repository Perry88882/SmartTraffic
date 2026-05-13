# Changelog

## v1.0.0 (2026-05-13)

### 新增
- **完整数据管道集成** — socket_handler 接入全链路：CaptureManager → packet_parser → flow_reassembly → feature_extractor → inference
- **SQLite 持久化** — database.py + schema.sql，三表设计（capture_session / flow / classification）含 8 个索引
- **真实网卡探测** — 基于 scapy get_windows_if_list 获取友好网卡名称，前端下拉框显示可读名称
- **WiFi 802.11 支持** — packet_parser 支持 RadioTap + Dot11 帧解析，过滤管理帧/控制帧
- **REST API 完善** — 新增 /api/status（管理员检测+运行模式）、/api/history（分页+标签筛选）
- **模型训练脚本** — train.py 支持合成数据生成 + 数据库真实数据导出 + RandomForest 训练
- **流超时清理** — FlowReassembler 按协议超时（TCP 60s / UDP 30s / ICMP 10s）自动清理过期流
- **WebSocket 传输升级** — 前端支持 websocket + polling 双传输

### 修复
- 修复每 5 包触发分类导致真实流量中分类从不触发的问题
- 修复 upsert_flow 计数逻辑（flow.packets 已包含全部包，不应累加旧值）
- 修复 inference.py 模型加载不兼容 train.py 输出的 dict wrapper 格式
- 修复 sniff() 无超时导致停止按钮在无流量时无法响应

### 变更
- app.py 添加 eventlet.monkey_patch() 确保异步引擎正确初始化
- ControlBar 重构：选中值改用 selectedName 以区分 name/display
- .gitignore 添加 backend/data/ 排除数据库文件

---

## v0.1.0 (2026-04-27)

### 新增
- Flask + SocketIO + eventlet 后端骨架
- React 18 + Vite + ECharts 前端仪表盘
- 占位 pipeline 模块（capture / feature / flow / inference）
- 纯模拟数据 WebSocket 推送
- 深色主题 CSS
- 一键启动脚本 run.py
