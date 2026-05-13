"""SmartTraffic 后端入口"""
import eventlet

# thread=False: 保留原生 OS 线程，避免 scapy 的 C 级 sniff() 阻塞 eventlet 事件循环导致后端卡死
eventlet.monkey_patch(thread=False)

import logging
import sys

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from api.routes import api_bp
from websocket.socket_handler import socket_manager, SmartTrafficNamespace

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

SECRET_KEY = "smarttraffic-dev"
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def main():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY

    CORS(app, origins=CORS_ORIGINS)
    app.register_blueprint(api_bp)

    socketio = SocketIO(
        app,
        cors_allowed_origins=CORS_ORIGINS,
        async_mode="eventlet",
        logger=False,
        engineio_logger=False,
    )

    socket_manager.init_app(socketio)
    socketio.on_namespace(SmartTrafficNamespace("/"))

    logger.info("[SmartTraffic] http://0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
