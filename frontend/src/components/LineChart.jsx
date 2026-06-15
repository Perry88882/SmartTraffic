import { useEffect, useRef, useMemo } from "react";
import * as echarts from "echarts";

const WINDOW_SIZE = 60;
const ALL_CATEGORIES = ["视频", "网页", "游戏", "下载", "会议", "音乐", "其他"];

const COLORS = [
  "#ff6b6b", "#4ecdc4", "#ffe66d", "#a29bfe",
  "#fd79a8", "#00cec9", "#636e72",
];

const AREA_GRADIENTS = [
  ["rgba(255,107,107,0.35)", "rgba(255,107,107,0.02)"],
  ["rgba(78,205,196,0.35)", "rgba(78,205,196,0.02)"],
  ["rgba(255,230,109,0.35)", "rgba(255,230,109,0.02)"],
  ["rgba(162,155,254,0.35)", "rgba(162,155,254,0.02)"],
  ["rgba(253,121,168,0.35)", "rgba(253,121,168,0.02)"],
  ["rgba(0,206,201,0.35)",  "rgba(0,206,201,0.02)"],
  ["rgba(99,110,114,0.35)", "rgba(99,110,114,0.02)"],
];

export default function LineChart({ records = [] }) {
  const chartRef = useRef(null);
  const instanceRef = useRef(null);

  // 计算每秒各类别数量
  const { timestamps, series } = useMemo(() => {
    const secMap = {};
    records.forEach((rec) => {
      const ts = rec.timestamp || rec.created_at || "";
      if (!ts) return;
      const sec = ts.slice(11, 19);
      if (!secMap[sec]) {
        secMap[sec] = {};
        ALL_CATEGORIES.forEach((c) => { secMap[sec][c] = 0; });
      }
      if (secMap[sec][rec.label] !== undefined) {
        secMap[sec][rec.label] += 1;
      }
    });
    const sorted = Object.keys(secMap).sort().slice(-WINDOW_SIZE);
    const tss = sorted.map((s) => s.slice(0, 5));

    const activeCats = new Set();
    sorted.forEach((sec) => {
      ALL_CATEGORIES.forEach((cat) => {
        if (secMap[sec][cat] > 0) activeCats.add(cat);
      });
    });

    const cats = ALL_CATEGORIES.filter((c) => activeCats.has(c));
    const sdata = cats.map((cat) => ({
      name: cat,
      data: sorted.map((sec) => secMap[sec][cat] || 0),
    }));

    return { timestamps: tss, series: sdata, activeCategories: cats };
  }, [records]);

  useEffect(() => {
    if (!chartRef.current) return;
    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current, null, {
        backgroundColor: "transparent",
      });
    }

    const chart = instanceRef.current;
    if (timestamps.length === 0) {
      chart.setOption({ series: [] });
      return;
    }

    chart.setOption({
      title: {
        text: "实时流量脉动",
        subtext: timestamps.length > 0 ? `${timestamps[0]} — ${timestamps[timestamps.length - 1]}` : "",
        left: "center",
        top: 6,
        textStyle: { color: "#e0e0e0", fontSize: 15, fontWeight: 700 },
        subtextStyle: { color: "#666", fontSize: 10 },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15,15,26,0.94)",
        borderColor: "#333",
        textStyle: { color: "#e0e0e0", fontSize: 12 },
        axisPointer: {
          type: "line",
          lineStyle: { color: "#444", type: "dashed" },
        },
      },
      legend: {
        data: series.map((s) => s.name),
        bottom: 0,
        textStyle: { color: "#aaa", fontSize: 10 },
        icon: "roundRect",
        itemWidth: 10,
        itemHeight: 10,
      },
      grid: { left: 45, right: 15, top: 55, bottom: 35 },
      xAxis: {
        type: "category",
        data: timestamps,
        axisLine: { lineStyle: { color: "#2a2a4a" } },
        axisTick: { show: false },
        axisLabel: {
          color: "#666",
          fontSize: 9,
          interval: Math.max(1, Math.floor(timestamps.length / 8)),
        },
      },
      yAxis: {
        type: "value",
        name: "条/秒",
        nameTextStyle: { color: "#666", fontSize: 10 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: "#1a1a2e" } },
        axisLabel: { color: "#666", fontSize: 10 },
        minInterval: 1,
      },
      series: series.map((s, i) => ({
        name: s.name,
        type: "line",
        data: s.data,
        smooth: true,
        symbol: "none",
        lineStyle: { color: COLORS[i % COLORS.length], width: 1.5 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: AREA_GRADIENTS[i % AREA_GRADIENTS.length][0] },
            { offset: 1, color: AREA_GRADIENTS[i % AREA_GRADIENTS.length][1] },
          ]),
        },
        emphasis: {
          focus: "series",
          lineStyle: { width: 2.5 },
        },
      })),
    });

    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [timestamps, series]);

  useEffect(() => {
    return () => {
      if (instanceRef.current) {
        instanceRef.current.dispose();
        instanceRef.current = null;
      }
    };
  }, []);

  // 无数据时展示占位
  if (timestamps.length === 0) {
    return (
      <div className="chart-container chart-placeholder">
        <span className="placeholder-text">等待数据流入…</span>
        <span className="placeholder-sub">点击"开始抓包"启动实时分析</span>
      </div>
    );
  }

  return <div ref={chartRef} className="chart-container" />;
}
