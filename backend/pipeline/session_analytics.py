"""
会话分析引擎 — 五层模型统计聚合
从 classification 表中提取会话维度的 5 层统计信息。
"""
from database import db


def build_layer_stats(session_id: int) -> dict:
    """
    为指定会话构建五层模型统计。

    Returns:
        { layers: { physical, datalink, network, transport, application }, summary }
    """
    conn = db.conn
    results = {}

    # ══════════════════════════════════════════════════════
    # 第 1 层: 物理层 — 包大小分布、速率时间线
    # ══════════════════════════════════════════════════════
    phys = {}
    sizes = conn.execute(
        "SELECT payload_size FROM classification WHERE session_id=?",
        (session_id,),
    ).fetchall()

    if sizes:
        s_list = [r["payload_size"] for r in sizes if r["payload_size"] and r["payload_size"] > 0]
        if not s_list:
            results["physical"] = phys
            results["datalink"] = {}
            results["network"] = {}
            results["transport"] = {}
            results["application"] = {}
            results["summary"] = {}
            return results
        phys["total_packets"] = len(s_list)
        phys["total_bytes"] = sum(s_list)
        phys["min_packet"] = min(s_list)
        phys["max_packet"] = max(s_list)
        phys["avg_packet"] = round(sum(s_list) / len(s_list), 1)
        phys["payload_total"] = sum(s_list)
        phys["payload_avg"] = phys["avg_packet"]
        # 包大小分布区间
        bins = {"< 100B": 0, "100-500B": 0, "500-1000B": 0, "1000-1500B": 0, "> 1500B": 0}
        for v in s_list:
            if v < 100:
                bins["< 100B"] += 1
            elif v < 500:
                bins["100-500B"] += 1
            elif v < 1000:
                bins["500-1000B"] += 1
            elif v <= 1500:
                bins["1000-1500B"] += 1
            else:
                bins["> 1500B"] += 1
        phys["size_distribution"] = bins
        # 速率数据（按分钟聚合）
        time_rows = conn.execute(
            "SELECT created_at, payload_size FROM classification WHERE session_id=? ORDER BY created_at",
            (session_id,),
        ).fetchall()
        if time_rows:
            minute_bytes = {}
            for r in time_rows:
                minute_key = r["created_at"][:16] if r["created_at"] else "?"
                minute_bytes[minute_key] = minute_bytes.get(minute_key, 0) + (r["payload_size"] or 0)
            phys["rate_timeline"] = [{"time": k, "bytes": v} for k, v in list(minute_bytes.items())[-20:]]

    results["physical"] = phys

    # ══════════════════════════════════════════════════════
    # 第 2 层: 数据链路层 — MAC 地址、帧类型
    # ══════════════════════════════════════════════════════
    dl = {}
    mac_rows = conn.execute(
        "SELECT src_mac, dst_mac, frame_type FROM classification WHERE session_id=? AND src_mac != ''",
        (session_id,),
    ).fetchall()

    if mac_rows:
        src_macs = {}
        dst_macs = {}
        ft = {"unicast": 0, "broadcast": 0, "multicast": 0, "unknown": 0}
        for r in mac_rows:
            if r["src_mac"]:
                src_macs[r["src_mac"]] = src_macs.get(r["src_mac"], 0) + 1
            if r["dst_mac"]:
                dst_macs[r["dst_mac"]] = dst_macs.get(r["dst_mac"], 0) + 1
            frame_t = r["frame_type"] or "unknown"
            ft[frame_t] = ft.get(frame_t, 0) + 1

        dl["unique_src_macs"] = len(src_macs)
        dl["unique_dst_macs"] = len(dst_macs)
        dl["top_src_macs"] = sorted(src_macs.items(), key=lambda x: -x[1])[:8]
        dl["top_dst_macs"] = sorted(dst_macs.items(), key=lambda x: -x[1])[:8]
        dl["frame_type_distribution"] = ft
        dl["total_mac_records"] = len(mac_rows)

    results["datalink"] = dl

    # ══════════════════════════════════════════════════════
    # 第 3 层: 网络层 — IP 地址、TTL、分片
    # ══════════════════════════════════════════════════════
    net = {}
    ip_rows = conn.execute(
        "SELECT src_ip, dst_ip, ttl, ip_version, ip_flags FROM classification WHERE session_id=?",
        (session_id,),
    ).fetchall()

    if ip_rows:
        src_ips = {}
        dst_ips = {}
        ttl_vals = []
        ipv4 = 0
        ipv6 = 0
        df_count = 0
        mf_count = 0

        for r in ip_rows:
            src_ips[r["src_ip"]] = src_ips.get(r["src_ip"], 0) + 1
            dst_ips[r["dst_ip"]] = dst_ips.get(r["dst_ip"], 0) + 1
            if r["ttl"] > 0:
                ttl_vals.append(r["ttl"])
            if r["ip_version"] == 6:
                ipv6 += 1
            else:
                ipv4 += 1
            if "DF" in (r["ip_flags"] or ""):
                df_count += 1
            if "MF" in (r["ip_flags"] or ""):
                mf_count += 1

        net["unique_src_ips"] = len(src_ips)
        net["unique_dst_ips"] = len(dst_ips)
        net["top_src_ips"] = sorted(src_ips.items(), key=lambda x: -x[1])[:10]
        net["top_dst_ips"] = sorted(dst_ips.items(), key=lambda x: -x[1])[:10]
        net["ipv4_count"] = ipv4
        net["ipv6_count"] = ipv6
        if ttl_vals:
            import statistics
            net["ttl_min"] = min(ttl_vals)
            net["ttl_max"] = max(ttl_vals)
            net["ttl_avg"] = round(statistics.mean(ttl_vals), 1)
            # TTL 分布
            ttl_bins = {}
            for t in ttl_vals:
                label = f"{t//16*16}-{t//16*16+15}"
                ttl_bins[label] = ttl_bins.get(label, 0) + 1
            net["ttl_distribution"] = dict(sorted(ttl_bins.items(), key=lambda x: int(x[0].split("-")[0])))
        net["df_flag_count"] = df_count
        net["mf_flag_count"] = mf_count

    results["network"] = net

    # ══════════════════════════════════════════════════════
    # 第 4 层: 传输层 — TCP/UDP、端口、标志位
    # ══════════════════════════════════════════════════════
    trans = {}
    port_rows = conn.execute(
        """SELECT protocol, src_port, dst_port, tcp_flags, window_size
           FROM classification WHERE session_id=?""",
        (session_id,),
    ).fetchall()

    if port_rows:
        tcp_count = 0
        udp_count = 0
        src_ports = {}
        dst_ports = {}
        flags_map = {}
        win_sizes = []

        for r in port_rows:
            if r["protocol"] == "TCP":
                tcp_count += 1
            elif r["protocol"] == "UDP":
                udp_count += 1
            if r["src_port"]:
                src_ports[r["src_port"]] = src_ports.get(r["src_port"], 0) + 1
            if r["dst_port"]:
                dst_ports[r["dst_port"]] = dst_ports.get(r["dst_port"], 0) + 1
            if r["tcp_flags"]:
                for f in r["tcp_flags"].split("/"):
                    flags_map[f] = flags_map.get(f, 0) + 1
            if r["window_size"] > 0:
                win_sizes.append(r["window_size"])

        trans["tcp_count"] = tcp_count
        trans["udp_count"] = udp_count
        trans["tcp_ratio"] = round(tcp_count / max(tcp_count + udp_count, 1) * 100, 1)
        trans["unique_src_ports"] = len(src_ports)
        trans["unique_dst_ports"] = len(dst_ports)
        trans["top_dst_ports"] = sorted(dst_ports.items(), key=lambda x: -x[1])[:10]
        trans["tcp_flags_distribution"] = dict(sorted(flags_map.items(), key=lambda x: -x[1]))
        if win_sizes:
            import statistics
            trans["window_avg"] = round(statistics.mean(win_sizes), 0)
            trans["window_max"] = max(win_sizes)

    results["transport"] = trans

    # ══════════════════════════════════════════════════════
    # 第 5 层: 应用层 — 标签分布、服务识别、域名
    # ══════════════════════════════════════════════════════
    app = {}
    cls_rows = conn.execute(
        "SELECT label, confidence, dst_port, protocol, payload_size FROM classification WHERE session_id=?",
        (session_id,),
    ).fetchall()

    if cls_rows:
        label_counts = {}
        conf_by_label = {}
        service_ports = {}
        total_payload = 0

        # 常见端口 → 服务名映射
        SERVICE_MAP = {
            443: "HTTPS", 80: "HTTP", 53: "DNS", 22: "SSH",
            8080: "HTTP-Alt", 8443: "HTTPS-Alt", 25: "SMTP",
            110: "POP3", 143: "IMAP", 993: "IMAPS", 21: "FTP",
            3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL",
        }

        for r in cls_rows:
            label = r["label"]
            label_counts[label] = label_counts.get(label, 0) + 1
            if label not in conf_by_label:
                conf_by_label[label] = []
            conf_by_label[label].append(r["confidence"])

            svc = SERVICE_MAP.get(r["dst_port"], f"Port-{r['dst_port']}")
            service_ports[svc] = service_ports.get(svc, 0) + 1
            total_payload += r["payload_size"] or 0

        total = sum(label_counts.values())
        app["label_distribution"] = {
            k: {"count": v, "pct": round(v / max(total, 1) * 100, 1)}
            for k, v in sorted(label_counts.items(), key=lambda x: -x[1])
        }
        app["label_avg_confidence"] = {
            k: round(sum(v) / len(v), 3) for k, v in conf_by_label.items()
        }
        app["service_distribution"] = dict(
            sorted(service_ports.items(), key=lambda x: -x[1])[:10]
        )
        app["total_payload_bytes"] = total_payload
        app["total_classifications"] = total

    results["application"] = app

    # ══════════════════════════════════════════════════════
    # 汇总
    # ══════════════════════════════════════════════════════
    results["summary"] = {
        "physical_pkts": phys.get("total_packets", 0),
        "datalink_macs": dl.get("total_mac_records", 0),
        "network_ips": net.get("unique_src_ips", 0) + net.get("unique_dst_ips", 0),
        "transport_tcp_pct": trans.get("tcp_ratio", 0),
        "application_labels": len(app.get("label_distribution", {})),
    }

    return results
