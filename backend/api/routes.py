"""REST API 路由"""
import logging
import platform

from flask import Blueprint, jsonify, request

from database import db
from websocket.socket_handler import socket_manager

api_bp = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


def _is_admin() -> bool:
    if platform.system() != "Windows":
        return True
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _get_real_interfaces() -> list[dict]:
    """返回网卡列表，每项含 name（scapy用）和 display（展示用）"""
    try:
        from scapy.config import conf
        conf.use_pcap = True
        conf.use_npcap = True

        if platform.system() == "Windows":
            try:
                from scapy.interfaces import get_windows_if_list
                raw = get_windows_if_list()
            except ImportError:
                raw = []
            result = []
            for iface in raw:
                name = iface.get("name", "")
                desc = iface.get("description", "")
                if not name:
                    continue
                # 跳过回环和无效接口
                if "loopback" in name.lower() or "loopback" in desc.lower():
                    continue
                # 用 description 作为展示名，太长则截短
                display = desc or name
                # Npcap 适配器描述通常以 "Npcap" 结尾，去掉冗余后缀
                for suffix in [" Npcap Loopback Adapter", " Npcap Packet Driver"]:
                    display = display.replace(suffix, "")
                display = display.strip()
                result.append({"name": name, "display": display})
            return result
        else:
            # Linux / macOS: get_if_list() 返回的名称已经可读 (eth0, wlan0...)
            from scapy.interfaces import get_if_list
            names = get_if_list()
            return [{"name": n, "display": n} for n in names if n != "lo"]
    except Exception:
        return []


def _list_interfaces() -> list[dict]:
    real = _get_real_interfaces()
    if real:
        return real
    return [
        {"name": "eth0", "display": "以太网 (eth0)"},
        {"name": "wlan0", "display": "无线网卡 (wlan0)"},
    ]


@api_bp.route("/cards", methods=["GET"])
def get_cards():
    return jsonify({"interfaces": _list_interfaces()})


@api_bp.route("/status", methods=["GET"])
def get_status():
    return jsonify({
        "is_admin": _is_admin(),
        "mode": socket_manager.mode,
        "is_running": socket_manager.is_running,
    })


@api_bp.route("/start", methods=["POST"])
def start_capture():
    body = request.get_json(silent=True) or {}
    iface = body.get("interface")
    if not iface:
        ifaces = _list_interfaces()
        iface = ifaces[0]["name"] if ifaces else "eth0"
    socket_manager.start(iface)
    return jsonify({"status": "started", "interface": iface})


@api_bp.route("/stop", methods=["POST"])
def stop_capture():
    socket_manager.stop()
    return jsonify({"status": "stopped"})


@api_bp.route("/history", methods=["GET"])
def get_history():
    session_id = request.args.get("session_id", type=int)
    label = request.args.get("label")
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    limit = min(limit, 500)
    records = db.query_history(session_id=session_id, label=label, limit=limit, offset=offset)
    total = db.get_history_count(session_id=session_id, label=label)

    return jsonify({"records": records, "total": total})
