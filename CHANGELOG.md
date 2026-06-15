# Changelog

## v1.2.0 (2026-06-15)

### 新增
- **GeoIP 物理地址识别** — `geoip.py` 离线嵌入式数据库，覆盖中国 20+ 省市 + 全球 60+ 国家/地区，IP → 城市/经纬度
- **赛博朋克 HUD UI** — 深空背景网格线 + 扫描线动画、霓虹渐变配色(青/紫/粉)、毛玻璃控制栏、卡片左侧色条
- **流畅动效系统** — 数据行 slideIn 动画、详情面板 slideUp 弹入、卡片 hover 上浮 + 阴影、按钮 glow 扩散、ECharts 渐变面积图

### 变更
- 折线图改为每秒统计 + 60 秒滑动窗口 + 渐变色填充
- 实时表格增至 20 行、50 条缓冲区
- PieChart / StatsBar / RecordTable 加 React.memo 避免无关重渲染
- 配色方案全面升级（青 `#00e5ff` / 紫 `#a855f7` / 粉 `#ec4899`）
- 统计卡片新增左侧色条装饰

---

## v1.1.0 (2026-05-13)

### 新增
- **五层模型分析** — packet_parser 提取完整 5 层字段（MAC/帧类型、TTL/IP版本/分片、TCP标志/窗口、载荷大小）；session_analytics 会话级聚合引擎；HistoryModal 五层标签页可视化（物理层/数据链路层/网络层/传输层/应用层）
- **AI 安全分析引擎** — security_analyzer.py：内置 40+ 条 IP 情报规则（Google/Cloudflare/腾讯/阿里/字节等），8 维度风险评估（端口风险/后门检测/协议异常/SYN扫描/TTL异常/横向移动/DNS隧道/高危端点），输出风险评分与等级
- **数据包详情面板** — 点击实时表格或历史记录任意行，展开五层协议详情 + 流量识别 + 安全评估卡片
- **历史记录增强** — 左侧会话列表显示接口/时间/流量/包数；日期筛选器（起止日期 + 快速跳转下拉）；删除会话功能（级联删除）
- **网卡智能筛选** — 三级兼容探测（get_windows_if_list → IFACES → get_if_list）；过滤虚拟/隧道适配器；按IP活跃度排序；显示网卡IP地址

### 修复
- 修复旧版 scapy 缺少 get_windows_if_list / IPv6 / Dot11 导致解析器对所有包返回 None
- 修复 eventlet monkey_patch 将 threading.Thread 变成协程导致 sniff() C调用阻塞整个事件循环
- 修复 sqlite3.Row 无 .get() 方法导致 session_analytics 500 错误
- 修复 analyze_traffic 在 try/except 外调用导致后台任务静默死亡
- 修复 statistics 字段 undefined 导致前端渲染空白

### 变更
- app.py monkey_patch 改为 thread=False 避免 scapy 阻塞
- 数据库新增 9 列五层字段 + analysis_json，自动迁移旧表
- 新增 API: GET /api/dates, DELETE /api/sessions/<id>
- /api/sessions 和 /api/history 支持 date_from/date_to 日期筛选

---

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
