"""
REST API 路由
提供网卡列表查询、抓包启停接口。
"""

from flask import Blueprint, jsonify, request

from websocket.socket_handler import socket_manager

api_bp = Blueprint("api", __name__, url_prefix="/api")

# 模拟可用网卡列表
AVAILABLE_INTERFACES = ["eth0", "wlan0", "lo"]


@api_bp.route("/cards", methods=["GET"])
def get_cards():
    """返回可用的网卡列表"""
    return jsonify({"interfaces": AVAILABLE_INTERFACES})


@api_bp.route("/start", methods=["POST"])
def start_capture():
    """
    启动抓包模拟。
    请求体: {"interface": "eth0"}
    """
    body = request.get_json(silent=True) or {}
    interface = body.get("interface", "eth0")
    socket_manager.start_simulation(interface)
    return jsonify({"status": "started", "interface": interface})


@api_bp.route("/stop", methods=["POST"])
def stop_capture():
    """停止抓包模拟"""
    socket_manager.stop_simulation()
    return jsonify({"status": "stopped"})
