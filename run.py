"""
SmartTraffic 一键启动脚本
同时启动后端（Flask）和前端（Vite）开发服务器。
需要 Python 3.10+ 和 Node.js 18+。
"""

import os
import subprocess
import sys
import threading
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def run_backend():
    """启动 Flask 后端"""
    backend_dir = os.path.join(PROJECT_ROOT, "backend")
    os.chdir(backend_dir)
    print("[run.py] 启动后端服务器 (Flask + SocketIO) ...")
    if sys.platform == "win32":
        subprocess.run([sys.executable, "app.py"])
    else:
        subprocess.run([sys.executable, "app.py"])


def run_frontend():
    """启动 Vite 前端开发服务器"""
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
    os.chdir(frontend_dir)
    print("[run.py] 启动前端开发服务器 (Vite) ...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    subprocess.run([npm_cmd, "run", "dev"])


def main():
    print("=" * 50)
    print("  SmartTraffic 一键启动")
    print("  后端: http://localhost:5000")
    print("  前端: http://localhost:5173")
    print("=" * 50)

    # 分别在不同线程中启动后端和前端
    backend_thread = threading.Thread(target=run_backend, name="backend", daemon=True)
    frontend_thread = threading.Thread(target=run_frontend, name="frontend", daemon=True)

    backend_thread.start()
    time.sleep(2)  # 稍等后端先启动
    frontend_thread.start()

    print("[run.py] 两个服务已启动，按 Ctrl+C 退出")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[run.py] 正在退出...")


if __name__ == "__main__":
    main()
