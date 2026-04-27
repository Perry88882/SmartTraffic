/**
 * 记录表格组件：展示最近 10 条流量识别记录。
 */
export default function RecordTable({ records = [] }) {
  return (
    <div className="table-card">
      <h3 className="table-title">最近识别记录</h3>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>源 IP</th>
              <th>目的 IP</th>
              <th>协议</th>
              <th>源端口</th>
              <th>目的端口</th>
              <th>分类</th>
              <th>置信度</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr>
                <td colSpan={8} className="empty-row">
                  暂无数据，请点击"开始抓包"
                </td>
              </tr>
            ) : (
              records.map((rec, idx) => (
                <tr key={idx}>
                  <td>{rec.timestamp || "-"}</td>
                  <td>{rec.src_ip}</td>
                  <td>{rec.dst_ip}</td>
                  <td>
                    <span className={`protocol-badge ${rec.protocol?.toLowerCase()}`}>
                      {rec.protocol}
                    </span>
                  </td>
                  <td>{rec.src_port}</td>
                  <td>{rec.dst_port}</td>
                  <td>
                    <span className="label-badge">{rec.label}</span>
                  </td>
                  <td>{(rec.confidence * 100).toFixed(1)}%</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
