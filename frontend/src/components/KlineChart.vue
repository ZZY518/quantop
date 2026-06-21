<template>
  <div v-if="rows.length === 0" class="chart-empty">暂无K线数据</div>
  <div v-else ref="chartRef" class="chart"></div>
</template>

<script setup lang="ts">
import * as echarts from "echarts";
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { ChartBar } from "@/lib/api";

const props = defineProps<{ rows: ChartBar[] }>();
const emit = defineEmits<{
  zoomChange: [zoom: { start: number; end: number }];
}>();
const chartRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

function render() {
  if (!chartRef.value || props.rows.length === 0) return;
  if (!chart) {
    chart = echarts.init(chartRef.value);
    chart.on("dataZoom", handleDataZoom);
  }

  const dates = props.rows.map((row) => row.trade_date);
  const kData = props.rows.map((row) => [num(row.open), num(row.close), num(row.low), num(row.high)]);
  const amountData = props.rows.map((row, index) => ({
    value: num(row.amount),
    itemStyle: { color: isUp(row, index) ? "#d93025" : "#008f5d" },
  }));
  const maxAmount = Math.max(...props.rows.map((row) => num(row.amount) || 0), 1);

  chart.setOption({
    animation: false,
    backgroundColor: "#ffffff",
    color: ["#f59e0b", "#2563eb", "#9333ea", "#64748b", "#94a3b8", "#ef4444", "#2563eb"],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
      borderColor: "#dce1e7",
      borderWidth: 1,
      padding: 10,
      textStyle: { color: "#18202a", fontSize: 12 },
      formatter: tooltipFormatter,
    },
    legend: {
      top: 2,
      left: 8,
      itemWidth: 16,
      itemHeight: 8,
      textStyle: { color: "#475467", fontSize: 12 },
      data: ["K线", "MA5", "MA10", "MA20", "MA60", "成交额", "MACD", "DIF", "DEA"],
    },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    grid: [
      { left: 56, right: 54, top: 34, height: "51%" },
      { left: 56, right: 54, top: "63%", height: "13%" },
      { left: 56, right: 54, top: "80%", height: "13%" },
    ],
    xAxis: [
      axis(dates, true),
      { ...axis(dates, false), gridIndex: 1, axisLabel: { show: false } },
      { ...axis(dates, true), gridIndex: 2 },
    ],
    yAxis: [
      priceAxis(),
      { ...valueAxis(), gridIndex: 1, max: maxAmount * 1.2, axisLabel: { formatter: amountLabel } },
      { ...valueAxis(), gridIndex: 2 },
    ],
    dataZoom: [
      { type: "inside", xAxisIndex: [0, 1, 2], start: zoomStart(), end: 100 },
      { type: "slider", xAxisIndex: [0, 1, 2], height: 22, bottom: 8, borderColor: "#dce1e7" },
    ],
    series: [
      {
        name: "K线",
        type: "candlestick",
        data: kData,
        barWidth: "58%",
        itemStyle: {
          color: "#d93025",
          color0: "#008f5d",
          borderColor: "#d93025",
          borderColor0: "#008f5d",
        },
      },
      maLine("MA5", props.rows.map((row) => num(row.ma5))),
      maLine("MA10", props.rows.map((row) => num(row.ma10))),
      maLine("MA20", props.rows.map((row) => num(row.ma20))),
      maLine("MA60", props.rows.map((row) => num(row.ma60))),
      {
        name: "成交额",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: amountData,
        barWidth: "58%",
      },
      {
        name: "MACD",
        type: "bar",
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: props.rows.map((row) => num(row.macd_hist)),
        barWidth: "5%",
        barMaxWidth: 8,
        itemStyle: {
          color: (params: { value: number }) => (params.value >= 0 ? "#d93025" : "#008f5d"),
        },
      },
      macdLine("DIF", props.rows.map((row) => num(row.macd))),
      macdLine("DEA", props.rows.map((row) => num(row.macd_signal))),
    ],
  });
}

function handleDataZoom() {
  if (!chart) return;
  const option = chart.getOption();
  const dataZoom = Array.isArray(option.dataZoom) ? option.dataZoom[0] : null;
  const start = Number(dataZoom?.start ?? 0);
  const end = Number(dataZoom?.end ?? 100);
  if (Number.isFinite(start) && Number.isFinite(end)) {
    emit("zoomChange", { start, end });
  }
}

function axis(data: string[], showLabel: boolean) {
  return {
    type: "category",
    data,
    boundaryGap: true,
    axisLine: { lineStyle: { color: "#dce1e7" }, onZero: false },
    axisTick: { show: false },
    axisLabel: { show: showLabel, color: "#667085", fontSize: 11 },
    splitLine: { show: false },
  };
}

function priceAxis() {
  return {
    scale: true,
    position: "right",
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: "#667085", fontSize: 11 },
    splitLine: { lineStyle: { color: "#eef1f4" } },
  };
}

function valueAxis() {
  return {
    scale: true,
    position: "right",
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: "#667085", fontSize: 11 },
    splitLine: { lineStyle: { color: "#eef1f4" } },
  };
}

function maLine(name: string, data: Array<number | null>) {
  return { name, type: "line", symbol: "none", smooth: true, lineStyle: { width: 1 }, data };
}

function macdLine(name: string, data: Array<number | null>) {
  return { name, type: "line", xAxisIndex: 2, yAxisIndex: 2, symbol: "none", lineStyle: { width: 1 }, data };
}

function tooltipFormatter(params: unknown) {
  const items = Array.isArray(params) ? params : [];
  const first = items[0] as { dataIndex?: number } | undefined;
  const index = first?.dataIndex ?? 0;
  const row = props.rows[index];
  if (!row) return "";
  const prevClose = index > 0 ? num(props.rows[index - 1].close) : null;
  const close = num(row.close) || 0;
  const change = prevClose == null ? null : close - prevClose;
  const pct = prevClose ? (change! / prevClose) * 100 : null;
  const cls = change == null || change >= 0 ? "tooltip-up" : "tooltip-down";
  return `
    <div class="chart-tooltip">
      <div class="tooltip-title">${row.trade_date}</div>
      <div>开盘 <b>${format(row.open)}</b>  最高 <b>${format(row.high)}</b></div>
      <div>收盘 <b class="${cls}">${format(row.close)}</b>  最低 <b>${format(row.low)}</b></div>
      <div>涨跌 <b class="${cls}">${change == null ? "-" : change.toFixed(2)}</b>  涨幅 <b class="${cls}">${pct == null ? "-" : pct.toFixed(2) + "%"}</b></div>
      <div>成交额 <b>${formatAmount(row.amount)}</b></div>
      <div>MA5 ${format(row.ma5)}  MA10 ${format(row.ma10)}  MA20 ${format(row.ma20)}  MA60 ${format(row.ma60)}</div>
      <div>MACD ${format(row.macd_hist)}  DIF ${format(row.macd)}  DEA ${format(row.macd_signal)}</div>
    </div>
  `;
}

function isUp(row: ChartBar, index: number) {
  if (index === 0) return (num(row.close) || 0) >= (num(row.open) || 0);
  return (num(row.close) || 0) >= (num(props.rows[index - 1].close) || 0);
}

function zoomStart() {
  if (props.rows.length <= 90) return 0;
  return Math.max(0, 100 - (90 / props.rows.length) * 100);
}

function num(value: number | string | null | undefined) {
  if (value == null) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function format(value: number | string | null | undefined) {
  const numeric = num(value);
  return numeric == null ? "-" : numeric.toFixed(2);
}

function amountLabel(value: number) {
  if (value >= 100000000) return `${(value / 100000000).toFixed(1)}亿`;
  if (value >= 10000) return `${(value / 10000).toFixed(0)}万`;
  return `${value}`;
}

function formatAmount(value: number | string | null | undefined) {
  const numeric = num(value);
  if (numeric == null) return "-";
  if (numeric >= 100000000) return `${(numeric / 100000000).toFixed(2)}亿`;
  if (numeric >= 10000) return `${(numeric / 10000).toFixed(2)}万`;
  return numeric.toFixed(2);
}

function resize() {
  chart?.resize();
}

async function renderAfterDomUpdate() {
  await nextTick();
  render();
}

onMounted(() => {
  renderAfterDomUpdate();
  window.addEventListener("resize", resize);
});
watch(() => props.rows, renderAfterDomUpdate, { deep: true });
onBeforeUnmount(() => {
  window.removeEventListener("resize", resize);
  chart?.off("dataZoom", handleDataZoom);
  chart?.dispose();
});
</script>
