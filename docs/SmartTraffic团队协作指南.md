# SmartTraffic 团队协作指南

## 一、环境准备

### 1. 安装 Git
- 下载地址：https://git-scm.com/download/win
- 安装时一路默认即可

### 2. 安装 Python 3.10+
- 下载地址：https://www.python.org/downloads/
- **安装时勾选 "Add Python to PATH"**

### 3. 安装 Node.js 18+
- 下载地址：https://nodejs.org/
- 选择 LTS 版本，安装时一路默认

### 4. 配置 Git 身份（打开终端执行）
```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

### 5. 配置 npm 镜像（国内加速）
```bash
npm config set registry https://registry.npmmirror.com
```

---

## 二、克隆项目

打开终端（PowerShell 或 CMD），进入你想存放项目的目录，执行：

```bash
git clone https://github.com/Perry88882/SmartTraffic.git
cd SmartTraffic
```

> 如果 GitHub 连不上，需要开 VPN/代理。或者让组长把代码打包发你。

---

## 三、安装依赖

### 后端依赖
```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 前端依赖
```bash
cd frontend
npm install
cd ..
```

---

## 四、启动项目

需要**同时开两个终端窗口**：

### 终端 1 — 启动后端
```bash
cd backend
python app.py
```
看到 `[SmartTraffic] 服务器启动: http://0.0.0.0:5000` 表示成功。

### 终端 2 — 启动前端
```bash
cd frontend
npm run dev
```
看到 `Local: http://localhost:5173` 表示成功。

然后用浏览器打开 **http://localhost:5173**，选择网卡，点击"开始抓包"就能看到效果。

---

## 五、团队协作流程

### 每次开始工作前（拉取最新代码）
```bash
git pull origin master
```

### 工作流程（三步走）
```bash
# 1. 添加你修改的文件
git add .

# 2. 提交（写清楚你改了什么）
git commit -m "修复了xxx问题 / 添加了xxx功能"

# 3. 推送到 GitHub
git push origin master
```

### ⚠️ 重要规则
1. **每天开工前先 `git pull`**，不然容易冲突
2. **提交信息写清楚**，别写 "update" 或 "fix"，要写 "修复饼图颜色不显示的问题"
3. **不要提交大文件**（超过 50MB 的模型文件、视频等）
4. **如果 push 失败**，说明别人已经提交了新代码，先 `git pull` 再 `git push`
5. **遇到冲突**，在群里喊一声，不要自己乱合并

---

## 六、项目结构速查

```
SmartTraffic/
├── backend/              ← Python 后端
│   ├── app.py            ← 程序入口
│   ├── config.py         ← 配置文件
│   ├── api/routes.py     ← API 接口
│   ├── websocket/        ← WebSocket 实时推送
│   └── pipeline/         ← 数据处理流水线（占位）
├── frontend/             ← React 前端
│   └── src/
│       ├── App.jsx       ← 主页面
│       └── components/   ← UI 组件
└── README.md
```

---

## 七、常见问题

| 问题 | 解决方法 |
|------|----------|
| `pip install` 慢 | `pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple` |
| `npm install` 慢 | `npm config set registry https://registry.npmmirror.com` |
| `python` 命令不存在 | 重新安装 Python 并勾选 "Add to PATH" |
| 端口 5000/5173 被占用 | 关闭之前运行的程序，或重启电脑 |
| 页面空白/图表不显示 | 打开浏览器控制台（F12），查看错误信息 |
| GitHub 连不上 | 开 VPN，或使用 `https://ghproxy.com/` 代理 |

---

有问题群里 @Perry88882
