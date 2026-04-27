"""
SmartTraffic 后端入口
启动 Flask + SocketIO 服务器，监听 0.0.0.0:5000。
"""

import logging
import sys

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from api.routes import api_bp
from config import CORS_ORIGINS, DEBUG, SECRET_KEY
from websocket.socket_handler import SmartTrafficNamespace, socket_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DEBUG"] = DEBUG

    # 配置 CORS
    CORS(app, origins=CORS_ORIGINS, supports_credentials=True)

    # 注册 API 蓝图
    app.register_blueprint(api_bp)

    logger.info("[SmartTraffic] Flask 应用初始化完成")
    return app


def main():
    app = create_app()

    # 初始化 SocketIO（eventlet 异步模式）
    socketio = SocketIO(
        app,
        cors_allowed_origins=CORS_ORIGINS,
        async_mode="eventlet",
        logger=DEBUG,
        engineio_logger=DEBUG,
    )

    # 注册 WebSocket 命名空间
    socketio.on_namespace(SmartTrafficNamespace("/"))

    logger.info("[SmartTraffic] 服务器启动: http://0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=DEBUG)


if __name__ == "__main__":
    main()
