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


def _is_junk_adapter(name: str, desc: str, ips: list) -> bool:
    """过滤掉不能抓包的虚拟/隧道适配器"""
    combined = f"{name} {desc}".lower()
    junk_patterns = [
        "wan miniport",       # WAN 隧道适配器
        "loopback",           # 回环
        "wi-fi direct",       # WiFi Direct 虚拟适配器
        "bluetooth",          # 蓝牙
    ]
    for pattern in junk_patterns:
        if pattern in combined:
            return True
    # APIPA 地址 (169.254.x.x) 表示网卡未连接网络，降低优先级但不排除
    return False


def _get_real_interfaces() -> list[dict]:
    """返回网卡列表，每项含 name（scapy用）、display（展示用）、ips"""
    try:
        from scapy.config import conf
        conf.use_pcap = True
        conf.use_npcap = True

        if platform.system() == "Windows":
            # 方案 1: get_windows_if_list（新版 scapy 2.5+），有 name + description
            try:
                from scapy.interfaces import get_windows_if_list
                raw = get_windows_if_list()
                result = []
                for item in raw:
                    name = item.get("name", "")
                    desc = item.get("description", name)
                    ips = item.get("ips", [])
                    if not name or _is_junk_adapter(name, desc, ips):
                        continue
                    display = desc or name
                    for suffix in [" Npcap Loopback Adapter", " Npcap Packet Driver"]:
                        display = display.replace(suffix, "")
                    display = display.strip()
                    result.append({"name": name, "display": display, "ips": ips})
                if result:
                    return _sort_interfaces(result)
            except ImportError:
                pass

            # 方案 2: IFACES（旧版 scapy 2.4.x），有 description 属性
            try:
                from scapy.interfaces import IFACES
                result = []
                for name, iface in IFACES.items():
                    desc = getattr(iface, "description", "") or name
                    ips = [ip for ip_list in getattr(iface, "ips", {}).values() for ip in ip_list]
                    if not name or _is_junk_adapter(name, desc, ips):
                        continue
                    display = desc.strip()
                    for suffix in [" Npcap Loopback Adapter", " Npcap Packet Driver"]:
                        display = display.replace(suffix, "")
                    display = display.strip()
                    result.append({"name": name, "display": display, "ips": ips})
                if result:
                    return _sort_interfaces(result)
            except Exception:
                pass

            # 方案 3: get_if_list（裸 NPF 名称，最后手段）
            from scapy.interfaces import get_if_list
            result = []
            for name in get_if_list():
                if not name or "loopback" in name.lower():
                    continue
                result.append({"name": name, "display": name, "ips": []})
            return result
        else:
            from scapy.interfaces import get_if_list
            names = get_if_list()
            return [{"name": n, "display": n, "ips": []} for n in names if n != "lo"]
    except Exception:
        return []


def _sort_interfaces(ifaces: list[dict]) -> list[dict]:
    """有真实 IP 的网卡排前面，APIPA/无 IP 的排后面"""
    def _key(item):
        ips = item.get("ips", [])
        has_real_ip = any(
            ip and not ip.startswith("169.254.") and ip != "0.0.0.0"
            for ip in ips
        )
        return (0 if has_real_ip else 1, item["display"])
    return sorted(ifaces, key=_key)


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
        "mode_reason": socket_manager.mode_reason,
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
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    limit = min(limit, 500)
    records = db.query_history(
        session_id=session_id, label=label,
        date_from=date_from, date_to=date_to,
        limit=limit, offset=offset,
    )
    total = db.get_history_count(
        session_id=session_id, label=label,
        date_from=date_from, date_to=date_to,
    )

    return jsonify({"records": records, "total": total})


@api_bp.route("/sessions", methods=["GET"])
def get_sessions():
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    sessions = db.get_sessions(limit=50, date_from=date_from, date_to=date_to)
    return jsonify({"sessions": sessions})


@api_bp.route("/dates", methods=["GET"])
def get_dates():
    """返回有数据的日期列表，供前端日期选择器使用"""
    dates = db.get_available_dates()
    return jsonify({"dates": dates})


@api_bp.route("/sessions/<int:session_id>", methods=["GET"])
def get_session_detail(session_id):
    detail = db.get_session_detail(session_id)
    if not detail:
        return jsonify({"error": "会话不存在"}), 404
    from pipeline.session_analytics import build_layer_stats
    analytics = build_layer_stats(session_id)
    detail["analytics"] = analytics
    return jsonify(detail)


@api_bp.route("/sessions/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    count = db.delete_session(session_id)
    return jsonify({"deleted": True, "classifications_removed": count})
