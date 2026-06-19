import { useState } from "react";

const RISK_COLORS = { 安全: "risk-safe", 注意: "risk-note", 可疑: "risk-warn", 高危: "risk-high" };

export default function RecordTable({ records = [] }) {
  const [selected, setSelected] = useState(null);

  return (
    <div className="table-card">
      <h3 className="table-title">最近识别记录 — 点击查看详情</h3>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>源 IP</th>
              <th>目的 IP / 组织</th>
              <th>协议</th>
              <th>目的</th>
              <th>分类</th>
              <th>风险</th>
              <th>置信度</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr><td colSpan={8} className="empty-row">暂无数据，请点击"开始抓包"</td></tr>
            ) : (
              records.map((rec, idx) => {
                const a = rec.analysis || {};
                return (
                  <tr
                    key={idx}
                    className={`record-row ${selected === idx ? "selected" : ""} ${a.suspicious ? "row-suspicious" : ""}`}
                    onClick={() => setSelected(selected === idx ? null : idx)}
                  >
                    <td>{rec.timestamp?.slice(11, 19) || "-"}</td>
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
        <PacketDetail rec={records[selected]} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function PacketDetail({ rec, onClose }) {
  const a = rec.analysis || {};

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

      {/* 安全分析区 */}
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
              <Field label="风险等级" value={a.risk_level || "-"}
                highlight={a.suspicious} />
              <Field label="风险评分" value={`${a.risk_score ?? 0}/100`}
                highlight={a.suspicious} />
              <Field label="综合备注" value={a.notes || "-"} />
            </div>
            {a.risk_reasons && a.risk_reasons.length > 0 && (
              <div className="risk-reasons">
                <div className="risk-reasons-title">风险详情:</div>
                {a.risk_reasons.map((r, i) => (
                  <div key={i} className="risk-reason-item">{r}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 五层协议区 */}
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
