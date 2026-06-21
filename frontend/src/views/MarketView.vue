<template>
  <div class="page">
    <section class="section">
      <div class="section-head">
        <div>
          <h1>市场行情</h1>
          <p class="muted">最近交易日 {{ latestDate || "-" }}，共 {{ rows.length }} 只股票</p>
        </div>
        <button class="secondary" @click="loadQuotes" :disabled="loading">
          {{ loading ? "刷新中" : "刷新" }}
        </button>
      </div>

      <div class="market-summary">
        <div>
          <span>上涨</span>
          <strong class="up">{{ upCount }}</strong>
        </div>
        <div>
          <span>下跌</span>
          <strong class="down">{{ downCount }}</strong>
        </div>
        <div>
          <span>平盘</span>
          <strong>{{ flatCount }}</strong>
        </div>
        <div>
          <span>成交额</span>
          <strong>{{ formatAmount(totalAmount) }}</strong>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>沪深A股</h2>
        <div class="segmented">
          <button :class="{ secondary: sortMode !== 'pct_desc' }" @click="sortMode = 'pct_desc'">涨幅</button>
          <button :class="{ secondary: sortMode !== 'pct_asc' }" @click="sortMode = 'pct_asc'">跌幅</button>
          <button :class="{ secondary: sortMode !== 'amount_desc' }" @click="sortMode = 'amount_desc'">成交额</button>
        </div>
      </div>

      <p class="error" v-if="error">{{ error }}</p>
      <div class="table-wrap">
        <table class="quote-table">
          <thead>
            <tr>
              <th>序号</th>
              <th>代码</th>
              <th>名称</th>
              <th>最新价</th>
              <th>涨跌幅</th>
              <th>涨跌额</th>
              <th>成交量</th>
              <th>成交额</th>
              <th>最高</th>
              <th>最低</th>
              <th>今开</th>
              <th>昨收</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in sortedRows" :key="`${row.symbol}-${row.trade_date}`">
              <td class="muted">{{ index + 1 }}</td>
              <td>
                <RouterLink class="text-link" :to="`/stock/${row.symbol}`">{{ row.symbol }}</RouterLink>
              </td>
              <td>{{ row.name || "-" }}</td>
              <td class="num" :class="valueClass(row.pct_chg)">{{ formatPrice(row.close) }}</td>
              <td class="num" :class="valueClass(row.pct_chg)">{{ formatPct(row.pct_chg) }}</td>
              <td class="num" :class="valueClass(row.change_amount)">{{ formatPrice(row.change_amount) }}</td>
              <td class="num">{{ formatVolume(row.volume) }}</td>
              <td class="num">{{ formatAmount(row.amount) }}</td>
              <td class="num">{{ formatPrice(row.high) }}</td>
              <td class="num">{{ formatPrice(row.low) }}</td>
              <td class="num">{{ formatPrice(row.open) }}</td>
              <td class="num">{{ formatPrice(row.pre_close) }}</td>
            </tr>
            <tr v-if="sortedRows.length === 0">
              <td colspan="12" class="muted">暂无行情数据，请先执行同步。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { apiGet, type Daily } from "@/lib/api";

type QuoteRow = Daily & { name?: string };
type SortMode = "pct_desc" | "pct_asc" | "amount_desc";

const rows = ref<QuoteRow[]>([]);
const loading = ref(false);
const error = ref("");
const sortMode = ref<SortMode>("pct_desc");

const latestDate = computed(() => rows.value[0]?.trade_date ?? "");
const upCount = computed(() => rows.value.filter((row) => Number(row.pct_chg ?? 0) > 0).length);
const downCount = computed(() => rows.value.filter((row) => Number(row.pct_chg ?? 0) < 0).length);
const flatCount = computed(() => rows.value.length - upCount.value - downCount.value);
const totalAmount = computed(() => rows.value.reduce((sum, row) => sum + Number(row.amount || 0), 0));
const sortedRows = computed(() => {
  const data = [...rows.value];
  if (sortMode.value === "pct_asc") {
    return data.sort((a, b) => Number(a.pct_chg ?? 0) - Number(b.pct_chg ?? 0));
  }
  if (sortMode.value === "amount_desc") {
    return data.sort((a, b) => Number(b.amount ?? 0) - Number(a.amount ?? 0));
  }
  return data.sort((a, b) => Number(b.pct_chg ?? 0) - Number(a.pct_chg ?? 0));
});

async function loadQuotes() {
  loading.value = true;
  error.value = "";
  try {
    rows.value = await apiGet<QuoteRow[]>("/market/quotes");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载市场行情失败";
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

function formatVolume(value: number | null | undefined) {
  if (value == null) return "-";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "-";
  if (numeric >= 1000000) return `${(numeric / 1000000).toFixed(2)}百万手`;
  if (numeric >= 10000) return `${(numeric / 10000).toFixed(2)}万手`;
  return numeric.toFixed(0);
}

function formatAmount(value: number | null | undefined) {
  if (value == null) return "-";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "-";
  if (numeric >= 100000000) return `${(numeric / 100000000).toFixed(2)}亿`;
  if (numeric >= 10000) return `${(numeric / 10000).toFixed(2)}万`;
  return numeric.toFixed(2);
}

onMounted(loadQuotes);
</script>
