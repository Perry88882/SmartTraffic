import { useState, useEffect, useCallback } from "react";
import axios from "axios";

const LAYER_NAMES = ["physical", "datalink", "network", "transport", "application"];
const LAYER_LABELS = {
  physical: "物理层",
  datalink: "数据链路层",
  network: "网络层",
  transport: "传输层",
  application: "应用层",
};
const LAYER_ICONS = {
  physical: "📡",
  datalink: "🔗",
  network: "🌐",
  transport: "📦",
  application: "📱",
};

function today() { return new Date().toISOString().slice(0, 10); }

export default function HistoryModal({ onClose }) {
  const [sessions, setSessions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [records, setRecords] = useState([]);
  const [labelFilter, setLabelFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("physical");
  const [viewMode, setViewMode] = useState("analytics");
  // 日期筛选
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [availableDates, setAvailableDates] = useState([]);

  const LABELS = ["视频", "游戏", "网页", "下载", "会议", "音乐", "其他"];

  const fetchSessions = useCallback(() => {
    const params = {};
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    axios.get("/api/sessions", { params }).then(r => {
      const list = r.data.sessions || [];
      setSessions(list);
      if (list.length > 0) setSelectedId(list[0].id);
      else setSelectedId(null);
    }).catch(() => {});
  }, [dateFrom, dateTo]);

  useEffect(() => {
    axios.get("/api/dates").then(r => {
      setAvailableDates(r.data.dates || []);
    }).catch(() => {});
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    axios.get(`/api/sessions/${selectedId}`).then(r => {
      setDetail(r.data);
      setLoading(false);
    }).catch(() => setLoading(false));
    // 同时获取分类记录
    const params = { session_id: selectedId, limit: 200 };
    if (labelFilter) params.label = labelFilter;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    axios.get("/api/history", { params }).then(r => {
      setRecords(r.data.records || []);
    }).catch(() => {});
  }, [selectedId, labelFilter]);

  const selectedSession = sessions.find(s => s.id === selectedId);

  const deleteSession = (id) => {
    if (!confirm(`确定删除会话 #${id} 及其所有分类记录吗？此操作不可恢复。`)) return;
    axios.delete(`/api/sessions/${id}`).then(() => {
      setSessions(prev => prev.filter(s => s.id !== id));
      if (selectedId === id) setSelectedId(null);
    }).catch(() => alert("删除失败"));
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>抓包记录 — 五层模型分析</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {/* 左侧: 会话列表 */}
          <div className="modal-sidebar">
            <h3>历史会话 ({sessions.length})</h3>

            {/* 日期筛选 */}
            <div className="date-filter">
              <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
                max={today()} className="date-input" title="开始日期" />
              <span className="date-sep">—</span>
              <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
                max={today()} className="date-input" title="结束日期" />
              {(dateFrom || dateTo) && (
                <button className="date-clear" onClick={() => { setDateFrom(""); setDateTo(""); }}>
                  &times;
                </button>
              )}
            </div>
            {availableDates.length > 0 && (
              <select className="date-quick" onChange={e => { setDateFrom(e.target.value); setDateTo(e.target.value); }} value="">
                <option value="">快速跳转日期...</option>
                {availableDates.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            )}

            <div className="session-list">
              {sessions.length === 0 && <p className="empty-hint">暂无记录</p>}
              {sessions.map(s => (
                <div
                  key={s.id}
                  className={`session-item ${s.id === selectedId ? "active" : ""}`}
                  onClick={() => setSelectedId(s.id)}
                >
                  <div className="session-item-row">
                    <div className="session-iface">{s.interface?.slice(-35)}</div>
                    <button className="session-delete" onClick={e => { e.stopPropagation(); deleteSession(s.id); }}
                      title="删除此会话">🗑</button>
                  </div>
                  <div className="session-time">{s.start_time?.replace("T", " ").slice(0, 16) || "-"}</div>
                  <div className="session-meta">
                    <span className={`session-status ${s.status}`}>{s.status === "running" ? "运行中" : "已停止"}</span>
                    <span>{fmtBytes(s.total_bytes)}</span>
                    <span>{s.total_packets} 包</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 右侧: 详情 */}
          <div className="modal-main">
            {loading ? (
              <p className="empty-hint">加载中...</p>
            ) : !detail ? (
              <p className="empty-hint">请选择一个会话</p>
            ) : (
              <>
                {/* 会话概览 */}
                <div className="session-overview">
                  <span className="overview-item">接口: <strong>{detail.interface}</strong></span>
                  <span className="overview-item">时间: {detail.start_time?.replace("T", " ").slice(0, 16)}</span>
                  <span className="overview-item">包: {detail.total_packets}</span>
                  <span className="overview-item">流量: {fmtBytes(detail.total_bytes)}</span>
                  <span className="overview-item">分类: {detail.total_classifications || 0}</span>
                </div>

                {/* 视图切换 */}
                <div className="view-toggle">
                  <button className={`toggle-btn ${viewMode === "analytics" ? "active" : ""}`}
                    onClick={() => setViewMode("analytics")}>五层分析</button>
                  <button className={`toggle-btn ${viewMode === "records" ? "active" : ""}`}
                    onClick={() => setViewMode("records")}>原始记录</button>
                </div>

                {viewMode === "analytics" ? (
                  <>
                    {/* 五层标签页 */}
                    <div className="layer-tabs">
                      {LAYER_NAMES.map(name => (
                        <button
                          key={name}
                          className={`layer-tab ${activeTab === name ? "active" : ""}`}
                          onClick={() => setActiveTab(name)}
                        >
                          {LAYER_ICONS[name]} {LAYER_LABELS[name]}
                        </button>
                      ))}
                    </div>

                    {/* 各层内容 */}
                    <div className="layer-content">
                      {activeTab === "physical" && <PhysicalLayer data={detail.analytics?.physical} />}
                      {activeTab === "datalink" && <DataLinkLayer data={detail.analytics?.datalink} />}
                      {activeTab === "network" && <NetworkLayer data={detail.analytics?.network} />}
                      {activeTab === "transport" && <TransportLayer data={detail.analytics?.transport} />}
                      {activeTab === "application" && <ApplicationLayer data={detail.analytics?.application} />}
                    </div>
                  </>
                ) : (
                  <HistoryRecords records={records} labelFilter={labelFilter} onFilterChange={setLabelFilter} labels={LABELS} />
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════
   历史记录详情表 — 可点击展开五层+安全分析
   ═══════════════════════════════════════════════ */

const RISK_COLORS = { 安全: "risk-safe", 注意: "risk-note", 可疑: "risk-warn", 高危: "risk-high" };

function HistoryRecords({ records, labelFilter, onFilterChange, labels }) {
  const [selected, setSelected] = useState(null);

  return (
    <>
      <div className="modal-main-header">
        <select value={labelFilter} onChange={e => onFilterChange(e.target.value)} className="filter-select">
          <option value="">全部类别</option>
          {labels.map(l => <option key={l} value={l}>{l}</option>)}
        </select>
      </div>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>时间</th><th>源 IP</th><th>目的 IP / 组织</th>
              <th>协议</th><th>目的</th><th>分类</th><th>风险</th><th>置信度</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr><td colSpan={8} className="empty-row">暂无数据</td></tr>
            ) : (
              records.map((rec, idx) => {
                const a = rec.analysis_json ? (() => { try { return JSON.parse(rec.analysis_json); } catch(e) { return {}; } })() : (rec.analysis || {});
                return (
                  <tr key={rec.id || idx}
                    className={`record-row ${selected === idx ? "selected" : ""} ${a.suspicious ? "row-suspicious" : ""}`}
                    onClick={() => setSelected(selected === idx ? null : idx)}>
                    <td>{rec.created_at?.slice(5, 19) || "-"}</td>
                    <td title={a.src_org}>{rec.src_ip}</td>
                    <td>
                      <div className="dst-cell">
                        <span>{rec.dst_ip}</span>
                        {a.dst_org && a.dst_org !== "未知" && a.dst_org !== "未知 (公网)" && (
                          <span className="org-tag">{a.dst_org}</span>
                        )}
                      </div>
                    </td>
                    <td><span className={`protocol-badge ${rec.protocol?.toLowerCase()}`}>{rec.protocol}</span></td>
                    <td className="purpose-cell" title={a.purpose}>{a.dst_service || rec.dst_port}</td>
                    <td><span className="label-badge">{rec.label}</span></td>
                    <td>
                      {a.risk_level ? (
                        <span className={`risk-badge ${RISK_COLORS[a.risk_level] || ""}`}>
                          {a.risk_level} {a.risk_score}
                        </span>
                      ) : "-"}
                    </td>
                    <td>{(rec.confidence * 100).toFixed(0)}%</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {selected !== null && records[selected] && (
        <HistoryPacketDetail rec={records[selected]} onClose={() => setSelected(null)} />
      )}
    </>
  );
}

function HistoryPacketDetail({ rec, onClose }) {
  const a = rec.analysis_json ? (() => { try { return JSON.parse(rec.analysis_json); } catch(e) { return {}; } })() : (rec.analysis || {});

  return (
    <div className="packet-detail">
      <div className="packet-detail-header">
        <h4>
          {a.suspicious ? "⚠️ " : ""}数据包分析
          {a.risk_level && (
            <span className={`risk-badge ${RISK_COLORS[a.risk_level] || ""} risk-badge-lg`}>
              {a.risk_level} — 评分 {a.risk_score}/100
            </span>
          )}
        </h4>
        <button className="modal-close" onClick={onClose}>&times;</button>
      </div>

      {Object.keys(a).length > 0 && (
        <div className="analysis-section">
          <div className="analysis-card">
            <div className="analysis-card-title">🎯 流量识别</div>
            <div className="analysis-grid">
              <Field label="源组织" value={a.src_org || "未知"} />
              <Field label="目标组织" value={a.dst_org || "未知"} highlight />
              <Field label="服务类型" value={a.dst_service || "未知"} />
              <Field label="流量目的" value={a.purpose || "-"} highlight />
            </div>
          </div>
          <div className="analysis-card">
            <div className="analysis-card-title">🛡️ 安全评估</div>
            <div className="analysis-grid">
              <Field label="风险等级" value={a.risk_level || "-"} highlight={a.suspicious} />
              <Field label="风险评分" value={`${a.risk_score ?? 0}/100`} highlight={a.suspicious} />
              <Field label="综合备注" value={a.notes || "-"} />
            </div>
            {a.risk_reasons && a.risk_reasons.length > 0 && (
              <div className="risk-reasons">
                <div className="risk-reasons-title">风险详情:</div>
                {a.risk_reasons.map((r, i) => <div key={i} className="risk-reason-item">{r}</div>)}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="packet-layers">
        <div className="packet-layer">
          <div className="packet-layer-title">🔗 数据链路层</div>
          <div className="packet-layer-grid">
            <Field label="源 MAC" value={rec.src_mac || "-"} mono />
            <Field label="目的 MAC" value={rec.dst_mac || "-"} mono />
            <Field label="帧类型" value={rec.frame_type || "-"} />
          </div>
        </div>
        <div className="packet-layer">
          <div className="packet-layer-title">🌐 网络层</div>
          <div className="packet-layer-grid">
            <Field label="源 IP" value={rec.src_ip} mono />
            <Field label="目的 IP" value={rec.dst_ip} mono />
            <Field label="TTL" value={rec.ttl || "-"} />
            <Field label="IP 版本" value={`IPv${rec.ip_version || 4}`} />
            <Field label="分片标志" value={rec.ip_flags || "无"} />
          </div>
        </div>
        <div className="packet-layer">
          <div className="packet-layer-title">📦 传输层</div>
          <div className="packet-layer-grid">
            <Field label="协议" value={rec.protocol} />
            <Field label="源端口" value={rec.src_port} />
            <Field label="目的端口" value={rec.dst_port} />
            <Field label="TCP 标志" value={rec.tcp_flags || "-"} />
            <Field label="窗口大小" value={rec.window_size ? `${rec.window_size} B` : "-"} />
          </div>
        </div>
        <div className="packet-layer">
          <div className="packet-layer-title">📱 应用层</div>
          <div className="packet-layer-grid">
            <Field label="载荷大小" value={rec.payload_size ? `${rec.payload_size} B` : "-"} />
            <Field label="AI 分类" value={rec.label} highlight />
            <Field label="置信度" value={`${(rec.confidence * 100).toFixed(1)}%`} highlight />
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, mono, highlight }) {
  return (
    <div className="packet-field">
      <span className="packet-field-label">{label}</span>
      <span className={`packet-field-value ${mono ? "mono" : ""} ${highlight ? "highlight" : ""}`}>
        {value ?? "-"}
      </span>
    </div>
  );
}

/* ═══════════════════════════════════════════════
   各层渲染组件
   ═══════════════════════════════════════════════ */

function StatRow({ label, value }) {
  return (
    <div className="stat-row">
      <span className="stat-row-label">{label}</span>
      <span className="stat-row-value">{value}</span>
    </div>
  );
}

function BarItem({ label, value, max }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="bar-item">
      <span className="bar-label">{label}</span>
      <div className="bar-track"><div className="bar-fill" style={{width: `${pct}%`}} /></div>
      <span className="bar-value">{value}</span>
    </div>
  );
}

function PhysicalLayer({ data }) {
  if (!data || !data.total_packets) return <p className="empty-hint">暂无物理层数据</p>;
  const dist = data.size_distribution || {};
  const maxDist = Math.max(1, ...Object.values(dist));
  return (
    <div className="layer-panel">
      <h3>📡 物理层 — 信号与比特传输</h3>
      <div className="layer-stats-grid">
        <StatRow label="总数据包" value={data.total_packets?.toLocaleString()} />
        <StatRow label="总流量" value={fmtBytes(data.total_bytes)} />
        <StatRow label="平均包大小" value={`${data.avg_packet} B`} />
        <StatRow label="最大包" value={`${data.max_packet} B`} />
        <StatRow label="最小包" value={`${data.min_packet} B`} />
        <StatRow label="有效载荷总量" value={fmtBytes(data.payload_total)} />
        <StatRow label="平均载荷" value={`${data.payload_avg} B`} />
      </div>
      <h4 className="section-subtitle">包大小分布</h4>
      {Object.entries(dist).map(([k, v]) => <BarItem key={k} label={k} value={v} max={maxDist} />)}
      {data.rate_timeline && data.rate_timeline.length > 0 && (
        <>
          <h4 className="section-subtitle">速率时间线 (每分钟字节数)</h4>
          <div className="rate-timeline">
            {data.rate_timeline.map((pt, i) => (
              <div key={i} className="rate-point" title={`${pt.time} — ${fmtBytes(pt.bytes)}`}>
                <div className="rate-bar" style={{height: `${Math.min(100, pt.bytes / Math.max(...data.rate_timeline.map(p=>p.bytes)) * 100)}%`}} />
                <span className="rate-label">{pt.time?.slice(11, 16)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function DataLinkLayer({ data }) {
  if (!data || !data.total_mac_records) return <p className="empty-hint">暂无数据链路层数据</p>;
  const ft = data.frame_type_distribution || {};
  const ftMax = Math.max(1, ...Object.values(ft));
  const topSrc = data.top_src_macs || [];
  const topDst = data.top_dst_macs || [];
  return (
    <div className="layer-panel">
      <h3>🔗 数据链路层 — 帧传输与MAC寻址</h3>
      <div className="layer-stats-grid">
        <StatRow label="源 MAC 数" value={data.unique_src_macs} />
        <StatRow label="目的 MAC 数" value={data.unique_dst_macs} />
        <StatRow label="MAC 记录总数" value={data.total_mac_records?.toLocaleString()} />
      </div>
      <h4 className="section-subtitle">帧类型分布</h4>
      {Object.entries(ft).map(([k, v]) => <BarItem key={k} label={k} value={v} max={ftMax} />)}
      {topSrc.length > 0 && (
        <>
          <h4 className="section-subtitle">Top 源 MAC</h4>
          <div className="mac-grid">
            {topSrc.map(([mac, cnt]) => <div key={mac} className="mac-chip">{mac} <span className="mac-count">{cnt}</span></div>)}
          </div>
        </>
      )}
      {topDst.length > 0 && (
        <>
          <h4 className="section-subtitle">Top 目的 MAC</h4>
          <div className="mac-grid">
            {topDst.map(([mac, cnt]) => <div key={mac} className="mac-chip">{mac} <span className="mac-count">{cnt}</span></div>)}
          </div>
        </>
      )}
    </div>
  );
}

function NetworkLayer({ data }) {
  if (!data || !data.unique_src_ips) return <p className="empty-hint">暂无网络层数据</p>;
  const topSrc = data.top_src_ips || [];
  const topDst = data.top_dst_ips || [];
  const maxSrc = topSrc[0]?.[1] || 1;
  const maxDst = topDst[0]?.[1] || 1;
  const ttlDist = data.ttl_distribution || {};
  const ttlMax = Math.max(1, ...Object.values(ttlDist));
  return (
    <div className="layer-panel">
      <h3>🌐 网络层 — IP 路由与寻址</h3>
      <div className="layer-stats-grid">
        <StatRow label="唯一源 IP" value={data.unique_src_ips} />
        <StatRow label="唯一目的 IP" value={data.unique_dst_ips} />
        <StatRow label="IPv4 包" value={data.ipv4_count?.toLocaleString()} />
        <StatRow label="IPv6 包" value={data.ipv6_count?.toLocaleString()} />
        <StatRow label="TTL 范围" value={`${data.ttl_min} ~ ${data.ttl_max} (avg ${data.ttl_avg})`} />
        <StatRow label="DF 分片标记" value={data.df_flag_count} />
        <StatRow label="MF 分片标记" value={data.mf_flag_count} />
      </div>
      <h4 className="section-subtitle">TTL 分布</h4>
      {Object.entries(ttlDist).map(([k, v]) => <BarItem key={k} label={k} value={v} max={ttlMax} />)}
      <h4 className="section-subtitle">Top 源 IP</h4>
      {topSrc.slice(0, 8).map(([ip, cnt]) => <BarItem key={ip} label={ip} value={cnt} max={maxSrc} />)}
      <h4 className="section-subtitle">Top 目的 IP</h4>
      {topDst.slice(0, 8).map(([ip, cnt]) => <BarItem key={ip} label={ip} value={cnt} max={maxDst} />)}
    </div>
  );
}

function TransportLayer({ data }) {
  if (!data || (!data.tcp_count && !data.udp_count)) return <p className="empty-hint">暂无传输层数据</p>;
  const flags = data.tcp_flags_distribution || {};
  const flagsMax = Math.max(1, ...Object.values(flags));
  const dstPorts = data.top_dst_ports || [];
  const portMax = dstPorts[0]?.[1] || 1;
  return (
    <div className="layer-panel">
      <h3>📦 传输层 — 端到端通信</h3>
      <div className="layer-stats-grid">
        <StatRow label="TCP 连接" value={data.tcp_count?.toLocaleString()} />
        <StatRow label="UDP 数据报" value={data.udp_count?.toLocaleString()} />
        <StatRow label="TCP 占比" value={`${data.tcp_ratio}%`} />
        <StatRow label="唯一源端口" value={data.unique_src_ports} />
        <StatRow label="唯一目的端口" value={data.unique_dst_ports} />
        {data.window_avg && <StatRow label="平均窗口大小" value={`${data.window_avg} B`} />}
        {data.window_max && <StatRow label="最大窗口" value={`${data.window_max} B`} />}
      </div>
      {Object.keys(flags).length > 0 && (
        <>
          <h4 className="section-subtitle">TCP 标志位分布</h4>
          {Object.entries(flags).map(([k, v]) => <BarItem key={k} label={k} value={v} max={flagsMax} />)}
        </>
      )}
      <h4 className="section-subtitle">Top 目的端口</h4>
      {dstPorts.map(([port, cnt]) => <BarItem key={port} label={`Port ${port}`} value={cnt} max={portMax} />)}
    </div>
  );
}

function ApplicationLayer({ data }) {
  if (!data || !data.total_classifications) return <p className="empty-hint">暂无应用层数据</p>;
  const labels = data.label_distribution || {};
  const services = data.service_distribution || {};
  const labelMax = Math.max(1, ...Object.values(labels).map(v => v.count));
  const svcMax = Math.max(1, ...Object.values(services));
  return (
    <div className="layer-panel">
      <h3>📱 应用层 — 服务与分类识别</h3>
      <div className="layer-stats-grid">
        <StatRow label="总分类数" value={data.total_classifications?.toLocaleString()} />
        <StatRow label="总载荷" value={fmtBytes(data.total_payload_bytes)} />
        <StatRow label="识别类别数" value={Object.keys(labels).length} />
      </div>
      <h4 className="section-subtitle">AI 分类分布</h4>
      {Object.entries(labels).map(([label, info]) => (
        <BarItem key={label} label={`${label} (${info.pct}%)`} value={info.count} max={labelMax} />
      ))}
      <h4 className="section-subtitle">平均置信度</h4>
      {data.label_avg_confidence && Object.entries(data.label_avg_confidence).map(([label, conf]) => (
        <StatRow key={label} label={label} value={`${(conf * 100).toFixed(1)}%`} />
      ))}
      <h4 className="section-subtitle">服务端口识别</h4>
      {Object.entries(services).map(([svc, cnt]) => <BarItem key={svc} label={svc} value={cnt} max={svcMax} />)}
    </div>
  );
}

function fmtBytes(b) {
  if (!b) return "0 B";
  const u = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(b) / Math.log(1024));
  return (b / Math.pow(1024, i)).toFixed(1) + " " + u[i];
}
