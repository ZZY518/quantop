<template>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>代码</th>
          <th>名称</th>
          <th>日期</th>
          <th>{{ mode === "score" ? "总分" : "涨跌幅" }}</th>
          <th v-if="mode === 'score'">趋势</th>
          <th v-if="mode === 'score'">动量</th>
          <th v-if="mode === 'daily'">收盘</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="`${row.symbol}-${row.trade_date}`">
          <td><RouterLink :to="`/stock/${row.symbol}`">{{ row.symbol }}</RouterLink></td>
          <td>{{ row.name || "-" }}</td>
          <td>{{ row.trade_date }}</td>
          <td :class="valueClass(mainValue(row))">{{ format(mainValue(row)) }}</td>
          <td v-if="mode === 'score'">{{ format(scoreTrend(row)) }}</td>
          <td v-if="mode === 'score'">{{ format(scoreMomentum(row)) }}</td>
          <td v-if="mode === 'daily'">{{ format(closePrice(row)) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { Daily, Factor } from "@/lib/api";

const props = defineProps<{
  rows: Array<(Daily | Factor) & { name?: string }>;
  mode: "daily" | "score";
}>();

function mainValue(row: (Daily | Factor) & { name?: string }) {
  return props.mode === "score" ? (row as Factor).total_score : (row as Daily).pct_chg;
}

function scoreTrend(row: (Daily | Factor) & { name?: string }) {
  return (row as Factor).score_trend;
}

function scoreMomentum(row: (Daily | Factor) & { name?: string }) {
  return (row as Factor).score_momentum;
}

function closePrice(row: (Daily | Factor) & { name?: string }) {
  return (row as Daily).close;
}

function format(value: number | null | undefined) {
  return value == null ? "-" : Number(value).toFixed(2);
}

function valueClass(value: number | null | undefined) {
  if (value == null) return "";
  return value >= 0 ? "up" : "down";
}
</script>
