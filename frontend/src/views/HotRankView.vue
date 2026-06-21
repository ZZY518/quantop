<template>
  <div class="page">
    <section class="section">
      <div class="section-head">
        <div>
          <h1>东方财富人气榜</h1>
        </div>
        <button class="secondary" @click="loadRows" :disabled="loading">
          {{ loading ? "刷新中..." : "刷新" }}
        </button>
      </div>

      <div class="market-summary">
        <div>
          <span>榜单数量</span>
          <strong>{{ rows.length }}</strong>
        </div>
        <div>
          <span>来源</span>
          <strong class="muted">东方财富</strong>
        </div>
        <div>
          <span>更新时间</span>
          <strong class="muted">{{ fetchedAt || "-" }}</strong>
        </div>
        <div>
          <span>首位代码</span>
          <strong>{{ rows[0]?.symbol || "-" }}</strong>
        </div>
      </div>

      <p class="error" v-if="error">{{ error }}</p>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>人气榜明细</h2>
      </div>

      <div class="table-wrap">
        <table class="quote-table hot-rank-table">
          <thead>
            <tr>
              <th>排名</th>
              <th>代码</th>
              <th>名称</th>
              <th>涨跌幅</th>
              <th>涨跌额</th>
              <th>最新价</th>
              <th>抓取时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="`${row.symbol}-${row.rank}`">
              <td class="muted">{{ row.rank }}</td>
              <td>
                <RouterLink class="text-link" :to="`/stock/${row.symbol}`">{{ row.symbol }}</RouterLink>
              </td>
              <td>{{ row.name }}</td>
              <td class="num" :class="valueClass(row.pct_chg)">{{ formatPct(row.pct_chg) }}</td>
              <td class="num" :class="valueClass(row.change_amount)">{{ formatPrice(row.change_amount) }}</td>
              <td class="num">{{ formatPrice(row.latest_price) }}</td>
              <td class="muted hot-rank-time">{{ formatTime(row.fetched_at) }}</td>
            </tr>
            <tr v-if="rows.length === 0">
              <td colspan="7" class="muted">暂无人气榜数据，请先刷新</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { apiGet, type HotRank } from "@/lib/api";

const rows = ref<HotRank[]>([]);
const loading = ref(false);
const error = ref("");
const fetchedAt = ref("");

async function loadRows() {
  loading.value = true;
  error.value = "";
  try {
    rows.value = await apiGet<HotRank[]>("/market/hot-rank?limit=50");
    fetchedAt.value = rows.value[0]?.fetched_at ? formatTime(rows.value[0].fetched_at) : "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载东方财富人气榜失败";
  } finally {
    loading.value = false;
  }
}

function valueClass(value: number | null | undefined) {
  const numeric = Number(value ?? 0);
  if (numeric > 0) return "up";
  if (numeric < 0) return "down";
  return "";
}

function formatPrice(value: number | null | undefined) {
  if (value == null) return "-";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(2) : "-";
}

function formatPct(value: number | null | undefined) {
  if (value == null) return "-";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toFixed(2)}%` : "-";
}

function formatTime(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

onMounted(loadRows);
</script>
