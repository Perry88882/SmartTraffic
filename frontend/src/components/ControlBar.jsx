import { useState, useEffect } from "react";
import axios from "axios";

/**
 * 顶部控制栏：
 *   网卡选择下拉框 + 开始/停止按钮 + 运行状态指示
 */
export default function ControlBar({ isRunning, onRunningChange, isConnected }) {
  const [interfaces, setInterfaces] = useState([]);
  const [selectedInterface, setSelectedInterface] = useState("eth0");
  const [loading, setLoading] = useState(false);

  // 页面加载时获取网卡列表
  useEffect(() => {
    axios
      .get("/api/cards")
      .then((res) => {
        const list = res.data.interfaces || [];
        setInterfaces(list);
        if (list.length > 0) setSelectedInterface(list[0]);
      })
      .catch((err) => {
        console.error("获取网卡列表失败:", err);
        // 降级使用默认列表
        setInterfaces(["eth0", "wlan0", "lo"]);
      });
  }, []);

  const handleStart = async () => {
    setLoading(true);
    try {
      await axios.post("/api/start", { interface: selectedInterface });
      onRunningChange(true);
    } catch (err) {
      console.error("启动抓包失败:", err);
      alert("启动失败，请确认后端服务已启动");
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await axios.post("/api/stop");
      onRunningChange(false);
    } catch (err) {
      console.error("停止抓包失败:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="control-bar">
      <h1 className="app-title">SmartTraffic 智能流量分析</h1>

      <div className="control-group">
        <label className="control-label">网卡</label>
        <select
          value={selectedInterface}
          onChange={(e) => setSelectedInterface(e.target.value)}
          disabled={isRunning}
          className="control-select"
        >
          {interfaces.map((iface) => (
            <option key={iface} value={iface}>
              {iface}
            </option>
          ))}
        </select>
      </div>

      {!isRunning ? (
        <button
          className="btn btn-start"
          onClick={handleStart}
          disabled={loading}
        >
          {loading ? "启动中..." : "开始抓包"}
        </button>
      ) : (
        <button
          className="btn btn-stop"
          onClick={handleStop}
          disabled={loading}
        >
          {loading ? "停止中..." : "停止抓包"}
        </button>
      )}

      <div className="status-indicator">
        <span className={`status-dot ${isRunning ? "running" : isConnected ? "idle" : "offline"}`} />
        <span className="status-text">
          {isRunning ? "运行中" : isConnected ? "待命中" : "离线"}
        </span>
      </div>
    </div>
  );
}
