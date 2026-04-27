import { useState, useEffect, useCallback } from "react";
import ControlBar from "./components/ControlBar";
import PieChart from "./components/PieChart";
import LineChart from "./components/LineChart";
import RecordTable from "./components/RecordTable";
import useWebSocket from "./hooks/useWebSocket";

/** 默认类别分布 */
const DEFAULT_DISTRIBUTION = {
  视频: 0,
  网页: 0,
  游戏: 0,
  下载: 0,
  会议: 0,
  音乐: 0,
  其他: 0,
};

export default function App() {
  const [isRunning, setIsRunning] = useState(false);
  const [categoryDistribution, setCategoryDistribution] = useState(DEFAULT_DISTRIBUTION);
  const [records, setRecords] = useState([]);
  const [totalStats, setTotalStats] = useState({
    total_bytes: 0,
    current_rate: 0,
    duration_seconds: 0,
  });

  const { lastMessage, isConnected } = useWebSocket();

  // 处理 WebSocket 推送的消息
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === "classification") {
      setRecords((prev) => {
        // 保留最近 50 条记录用于图表，表格仅展示最近 10 条
        const next = [lastMessage.data, ...prev];
        return next.slice(0, 50);
      });
    }

    if (lastMessage.type === "statistics") {
      setCategoryDistribution(lastMessage.data.category_distribution);
      setTotalStats({
        total_bytes: lastMessage.data.total_bytes,
        current_rate: lastMessage.data.current_rate,
        duration_seconds: lastMessage.data.duration_seconds,
      });
    }
  }, [lastMessage]);

  const handleRunningChange = useCallback((running) => {
    setIsRunning(running);
  }, []);

  return (
    <div className="app-container">
      {/* 顶部控制栏 */}
      <ControlBar
        isRunning={isRunning}
        onRunningChange={handleRunningChange}
        isConnected={isConnected}
      />

      {/* 统计概览 */}
      <div className="stats-overview">
        <div className="stat-card">
          <span className="stat-label">总流量</span>
          <span className="stat-value">{formatBytes(totalStats.total_bytes)}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">当前速率</span>
          <span className="stat-value">{formatBytes(totalStats.current_rate)}/s</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">运行时长</span>
          <span className="stat-value">{formatDuration(totalStats.duration_seconds)}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">连接状态</span>
          <span className={`stat-value ${isConnected ? "connected" : "disconnected"}`}>
            {isConnected ? "已连接" : "未连接"}
          </span>
        </div>
      </div>

      {/* 中间图表区域 */}
      <div className="charts-row">
        <PieChart distribution={categoryDistribution} />
        <LineChart records={records} />
      </div>

      {/* 底部记录表格 */}
      <RecordTable records={records.slice(0, 10)} />
    </div>
  );
}

/** 格式化字节数为可读字符串 */
function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(2) + " " + units[i];
}

/** 格式化秒数为 HH:MM:SS */
function formatDuration(seconds) {
  if (!seconds) return "00:00:00";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [h, m, s].map((v) => String(v).padStart(2, "0")).join(":");
}
