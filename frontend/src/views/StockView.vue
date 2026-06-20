<template>
  <div class="page">
    <section class="section stock-header" v-if="stock">
      <div>
        <h1>{{ stock.name }} {{ stock.symbol }}</h1>
        <p class="muted">{{ stock.market }} / {{ stock.exchange }} / {{ stock.industry || "-" }}</p>
      </div>
      <div class="quote-strip" v-if="latestBar">
        <div>
          <span>最新</span>
          <strong :class="changeClass">{{ format(latestBar.close) }}</strong>
        </div>
        <div>
          <span>涨跌</span>
          <strong :class="changeClass">{{ format(changeAmount) }}</strong>
        </div>
        <div>
          <span>涨幅</span>
          <strong :class="changeClass">{{ formatPct(changePct) }}</strong>
        </div>
        <div>
          <span>最高</span>
          <strong>{{ format(latestBar.high) }}</strong>
        </div>
        <div>
          <span>最低</span>
          <strong>{{ format(latestBar.low) }}</strong>
        </div>
        <div>
          <span>成交额</span>
          <strong>{{ formatAmount(latestBar.amount) }}</strong>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>K线行情 <span class="muted count-text">{{ chartRows.length }} bars</span></h2>
        <div class="segmented">
          <button
            v-for="item in periods"
            :key="item.value"
            :class="{ secondary: period !== item.value }"
            @click="setPeriod(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>
      <KlineChart :rows="chartRows" @zoom-change="chartZoom = $event" />
    </section>

    <section class="section">
      <h2>因子趋势</h2>
      <FactorChart :rows="factors" :zoom="chartZoom" />
    </section>

    <section class="section">
      <h2>最近因子</h2>
      <RankTable :rows="latestFactorRows" mode="score" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import FactorChart from "@/components/FactorChart.vue";
import KlineChart from "@/components/KlineChart.vue";
import RankTable from "@/components/RankTable.vue";
import { apiGet, type ChartBar, type Factor, type Stock } from "@/lib/api";

const props = defineProps<{ symbol: string }>();
const stock = ref<Stock | null>(null);
const chartRows = ref<ChartBar[]>([]);
const factors = ref<Factor[]>([]);
const period = ref("1d");
const chartZoom = ref<{ start: number; end: number } | undefined>();
const periods = [
  { label: "日线", value: "1d" },
  { label: "周线", value: "1w" },
  { label: "月线", value: "1m" },
];

const latestBar = computed(() => chartRows.value[chartRows.value.length - 1] || null);
const previousBar = computed(() => (chartRows.value.length > 1 ? chartRows.value[chartRows.value.length - 2] : null));
const changeAmount = computed(() => {
  if (!latestBar.value || !previousBar.value) return null;
  return Number(latestBar.value.close) - Number(previousBar.value.close);
});
const changePct = computed(() => {
  if (changeAmount.value == null || !previousBar.value) return null;
  const prev = Number(previousBar.value.close);
  return prev ? (changeAmount.value / prev) * 100 : null;
});
const changeClass = computed(() => (changeAmount.value == null || changeAmount.value >= 0 ? "up" : "down"));
const latestFactorRows = computed(() =>
  factors.value.slice(-20).reverse().map((row) => ({ ...row, name: stock.value?.name })),
);

onMounted(async () => {
  stock.value = await apiGet<Stock>(`/stocks/${props.symbol}`);
  await loadPeriod();
});

async function loadPeriod() {
  chartZoom.value = undefined;
  [chartRows.value, factors.value] = await Promise.all([
    apiGet<ChartBar[]>(`/stocks/${props.symbol}/chart?period=${period.value}&limit=240`),
    apiGet<Factor[]>(`/stocks/${props.symbol}/bar-factors?period=${period.value}&limit=240`),
  ]);
}

async function setPeriod(value: string) {
  period.value = value;
  await loadPeriod();
}

function format(value: number | string | null | undefined) {
  if (value == null) return "-";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(2) : "-";
}

function formatPct(value: number | null) {
  return value == null ? "-" : `${value.toFixed(2)}%`;
}

function formatAmount(value: number | string | null | undefined) {
  if (value == null) return "-";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "-";
  if (numeric >= 100000000) return `${(numeric / 100000000).toFixed(2)}亿`;
  if (numeric >= 10000) return `${(numeric / 10000).toFixed(2)}万`;
  return numeric.toFixed(2);
}
</script>
