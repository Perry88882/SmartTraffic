import { useState, useEffect, useCallback, memo } from "react";
import ControlBar from "./components/ControlBar";
import PieChart from "./components/PieChart";
import LineChart from "./components/LineChart";
import RecordTable from "./components/RecordTable";
import HistoryModal from "./components/HistoryModal";
import useWebSocket from "./hooks/useWebSocket";

const EMPTY_DIST = { 视频: 0, 网页: 0, 游戏: 0, 下载: 0, 会议: 0, 音乐: 0, 其他: 0 };

export default function App() {
  const [isRunning, setIsRunning] = useState(false);
  const [distribution, setDistribution] = useState(EMPTY_DIST);
  const [records, setRecords] = useState([]);
  const [stats, setStats] = useState({
    total_bytes: 0, current_rate: 0, total_packets: 0, duration_seconds: 0,
  });
  const [showHistory, setShowHistory] = useState(false);

  const { lastMessage, isConnected } = useWebSocket();

  const handleRunningChange = useCallback((running) => {
    setIsRunning(running);
    if (!running) {
      setDistribution(EMPTY_DIST);
      setRecords([]);
      setStats({ total_bytes: 0, current_rate: 0, total_packets: 0, duration_seconds: 0 });
    }
  }, []);

  useEffect(() => {
    if (!lastMessage) return;
    const d = lastMessage.data;
    if (lastMessage.type === "classification") {
      setRecords((prev) => [d, ...prev].slice(0, 60));
    }
    if (lastMessage.type === "statistics") {
      setDistribution(d.category_distribution || EMPTY_DIST);
      setStats({
        total_bytes: d.total_bytes || 0,
        current_rate: d.current_rate || 0,
        total_packets: d.total_packets || 0,
        duration_seconds: d.duration_seconds || 0,
      });
    }
  }, [lastMessage]);

  return (
    <div className="app-container">
      <ControlBar
        isRunning={isRunning}
        onRunningChange={handleRunningChange}
        isConnected={isConnected}
        onShowHistory={() => setShowHistory(true)}
      />

      {showHistory && <HistoryModal onClose={() => setShowHistory(false)} />}

      <StatsBar stats={stats} />

      <div className="charts-row">
        <PieChart distribution={distribution} />
        <LineChart records={records} />
      </div>

      <RecordTable records={records} />
    </div>
  );
}

const StatsBar = memo(function StatsBar({ stats }) {
  return (
    <div className="stats-overview">
      <StatCard label="总流量"   value={fmtBytes(stats.total_bytes)} />
      <StatCard label="当前速率" value={fmtBytes(stats.current_rate) + "/s"} />
      <StatCard label="总包数"   value={stats.total_packets.toLocaleString()} />
      <StatCard label="运行时长" value={fmtTime(stats.duration_seconds)} />
    </div>
  );
});

function StatCard({ label, value }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

function fmtBytes(b) {
  if (!b) return "0 B";
  const u = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(b) / Math.log(1024));
  return (b / Math.pow(1024, i)).toFixed(1) + " " + u[i];
}

function fmtTime(s) {
  if (!s) return "00:00";
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0");
}
