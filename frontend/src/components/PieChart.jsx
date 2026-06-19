import { useEffect, useRef } from "react";
import * as echarts from "echarts";

export default function PieChart({ distribution }) {
  const chartRef = useRef(null);
  const instanceRef = useRef(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // 初始化 ECharts 实例
    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current, null, {
        backgroundColor: "transparent",
      });
    }

    const chart = instanceRef.current;
    const data = Object.entries(distribution || {}).map(([name, value]) => ({
      name,
      value,
    }));

    chart.setOption({
      title: {
        text: "流量类别分布",
        left: "center",
        textStyle: { color: "#e0e0e0", fontSize: 14 },
      },
      tooltip: {
        trigger: "item",
        formatter: "{b}: {c} 条 ({d}%)",
      },
      legend: {
        bottom: 0,
        textStyle: { color: "#aaa", fontSize: 11 },
      },
      series: [
        {
          type: "pie",
          radius: ["40%", "70%"],
          center: ["50%", "48%"],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 4,
            borderColor: "#1a1a2e",
            borderWidth: 2,
          },
          label: {
            show: false,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: "bold",
            },
          },
          data,
        },
      ],
    });

    // 响应窗口大小变化
    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, [distribution]);

  // 清理实例
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
