import { useEffect, useRef } from "react";
import * as echarts from "echarts";

/**
 * 折线图组件：展示最近识别记录的时间分布（按类别数量变化趋势）。
 * 简化实现：统计各类别随时间累积的条目数，绘制折线图。
 */
export default function LineChart({ records = [] }) {
  const chartRef = useRef(null);
  const instanceRef = useRef(null);

  useEffect(() => {
    if (!chartRef.current) return;

    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current, null, {
        backgroundColor: "transparent",
      });
    }

    const chart = instanceRef.current;

    // records 按时间正序排列（最早的在前面）
    const sorted = [...records].reverse();

    const categories = ["视频", "网页", "游戏", "下载", "会议", "音乐", "其他"];
    const seriesData = {};
    categories.forEach((cat) => {
      seriesData[cat] = [];
    });

    // 构建累积计数
    const timestamps = [];
    const counters = {};
    categories.forEach((cat) => {
      counters[cat] = 0;
    });

    sorted.forEach((rec) => {
      const ts = rec.timestamp || "";
      timestamps.push(ts);
      if (counters[rec.label] !== undefined) {
        counters[rec.label] += 1;
      }
      categories.forEach((cat) => {
        seriesData[cat].push(counters[cat]);
      });
    });

    chart.setOption({
      title: {
        text: "识别趋势",
        left: "center",
        textStyle: { color: "#e0e0e0", fontSize: 14 },
      },
      tooltip: {
        trigger: "axis",
      },
      legend: {
        data: categories,
        bottom: 0,
        textStyle: { color: "#aaa", fontSize: 10 },
      },
      xAxis: {
        type: "category",
        data: timestamps,
        axisLabel: {
          color: "#888",
          rotate: 30,
          fontSize: 10,
          formatter: (val) => (val ? val.slice(-8) : ""), // 仅显示时分秒
        },
      },
      yAxis: {
        type: "value",
        name: "累计识别数",
        nameTextStyle: { color: "#888" },
        axisLabel: { color: "#888" },
      },
      series: categories.map((cat) => ({
        name: cat,
        type: "line",
        data: seriesData[cat],
        smooth: true,
        symbol: "none",
      })),
    });

    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [records]);

  useEffect(() => {
    return () => {
      if (instanceRef.current) {
        instanceRef.current.dispose();
        instanceRef.current = null;
      }
    };
  }, []);

  return <div ref={chartRef} className="chart-container" />;
}
