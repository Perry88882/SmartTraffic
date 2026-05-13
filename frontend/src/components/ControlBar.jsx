import { useState, useEffect } from "react";
import axios from "axios";

export default function ControlBar({ isRunning, onRunningChange, isConnected }) {
  const [ifaces, setIfaces] = useState([]);
  const [selectedName, setSelectedName] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState({ is_admin: false, mode: "detecting", is_running: false });

  useEffect(() => {
    axios.get("/api/status").then(r => {
      setStatus(r.data);
      if (r.data.is_running) onRunningChange(true);
    }).catch(() => {});

    axios.get("/api/cards").then(r => {
      const list = r.data.interfaces || [];
      setIfaces(list);
      if (list.length > 0) setSelectedName(list[0].name);
    }).catch(() => {
      setIfaces([
        { name: "eth0", display: "以太网 (eth0)" },
        { name: "wlan0", display: "无线网卡 (wlan0)" },
      ]);
      setSelectedName("eth0");
    });
  }, []);

  const start = () => {
    setBusy(true);
    axios.post("/api/start", { interface: selectedName }).then(() => {
      onRunningChange(true);
      setBusy(false);
    }).catch(() => setBusy(false));
  };

  const stop = () => {
    setBusy(true);
    axios.post("/api/stop").then(() => {
      onRunningChange(false);
      setBusy(false);
    }).catch(() => setBusy(false));
  };

  const modeLabel = status.mode === "real" ? "真实抓包" : status.mode === "simulated" ? "模拟模式" : "检测中";
  const modeClass = `mode-badge mode-${status.mode}`;

  return (
    <div className="control-bar">
      <h1 className="app-title">SmartTraffic</h1>

      {!status.is_admin && (
        <span className="admin-warning">非管理员 — 将使用模拟数据</span>
      )}
      <span className={modeClass}>{modeLabel}</span>

      <select
        value={selectedName}
        onChange={e => setSelectedName(e.target.value)}
        disabled={isRunning}
        className="control-select"
      >
        {ifaces.length === 0 && <option value="">无可用网卡</option>}
        {ifaces.map(i => (
          <option key={i.name} value={i.name}>{i.display}</option>
        ))}
      </select>

      {isRunning ? (
        <button className="btn btn-stop" onClick={stop} disabled={busy}>
          {busy ? "..." : "停止"}
        </button>
      ) : (
        <button className="btn btn-start" onClick={start} disabled={busy || ifaces.length === 0}>
          {busy ? "..." : "开始抓包"}
        </button>
      )}

      <span className="status-indicator">
        <span className={`status-dot ${isRunning ? "running" : isConnected ? "idle" : "offline"}`} />
        <span className="status-text" style={{color: isConnected ? "#00d2a0" : "#ff4757"}}>
          {isConnected ? "已连接" : "未连接"}
        </span>
      </span>
    </div>
  );
}
