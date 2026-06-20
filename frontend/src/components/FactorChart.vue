<template>
  <div ref="chartRef" class="chart"></div>
</template>

<script setup lang="ts">
import * as echarts from "echarts";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { Factor } from "@/lib/api";

const props = defineProps<{
  rows: Factor[];
  zoom?: { start: number; end: number };
}>();
const chartRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

function render() {
  if (!chartRef.value) return;
  if (!chart) chart = echarts.init(chartRef.value);
  chart.setOption({
    tooltip: { trigger: "axis" },
    legend: { top: 0 },
    grid: { left: 48, right: 24, top: 42, bottom: 36 },
    xAxis: { type: "category", data: props.rows.map((row) => row.trade_date) },
    yAxis: { type: "value", min: 0, max: 100 },
    dataZoom: [
      { type: "inside", start: props.zoom?.start ?? zoomStart(), end: props.zoom?.end ?? 100 },
      { type: "slider", height: 18, bottom: 8, start: props.zoom?.start ?? zoomStart(), end: props.zoom?.end ?? 100 },
    ],
    series: [
      { name: "总分", type: "line", smooth: true, data: props.rows.map((row) => row.total_score) },
      { name: "趋势", type: "line", smooth: true, data: props.rows.map((row) => row.score_trend) },
      { name: "动量", type: "line", smooth: true, data: props.rows.map((row) => row.score_momentum) },
    ],
  });
}

function zoomStart() {
  if (props.rows.length <= 90) return 0;
  return Math.max(0, 100 - (90 / props.rows.length) * 100);
}

function resize() {
  chart?.resize();
}

onMounted(() => {
  render();
  window.addEventListener("resize", resize);
});
watch(() => props.rows, render, { deep: true });
watch(() => props.zoom, render, { deep: true });
onBeforeUnmount(() => {
  window.removeEventListener("resize", resize);
  chart?.dispose();
});
</script>
