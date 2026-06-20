<template>
  <div class="page">
    <section class="section">
      <h1>市场总览</h1>
      <div class="grid">
        <MetricCard label="数据库股票数" :value="stocks.length" />
        <MetricCard label="涨幅榜样本" :value="dailyRank.length" />
        <MetricCard label="评分榜样本" :value="scoreRank.length" />
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>全部股票</h2>
        <RouterLink class="text-link" to="/market">查看完整列表</RouterLink>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>市场</th>
              <th>交易所</th>
              <th>行业</th>
              <th>行情</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="stock in stocks" :key="stock.symbol">
              <td>
                <RouterLink class="text-link" :to="`/stock/${stock.symbol}`">{{ stock.symbol }}</RouterLink>
              </td>
              <td>{{ stock.name }}</td>
              <td>{{ stock.market }}</td>
              <td>{{ stock.exchange }}</td>
              <td>{{ stock.industry || "-" }}</td>
              <td>
                <RouterLink class="text-link" :to="`/stock/${stock.symbol}`">K线</RouterLink>
              </td>
            </tr>
            <tr v-if="stocks.length === 0">
              <td colspan="6" class="muted">暂无股票数据，请先执行同步。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="grid">
      <div class="section">
        <h2>涨幅榜</h2>
        <RankTable :rows="dailyRank" mode="daily" />
      </div>
      <div class="section">
        <h2>评分榜</h2>
        <RankTable :rows="scoreRank" mode="score" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import MetricCard from "@/components/MetricCard.vue";
import RankTable from "@/components/RankTable.vue";
import { apiGet, type Daily, type Factor, type Stock } from "@/lib/api";

const stocks = ref<Stock[]>([]);
const dailyRank = ref<Array<Daily & { name?: string }>>([]);
const scoreRank = ref<Array<Factor & { name?: string }>>([]);

onMounted(async () => {
  [stocks.value, dailyRank.value, scoreRank.value] = await Promise.all([
    apiGet<Stock[]>("/stocks"),
    apiGet<Array<Daily & { name?: string }>>("/market/rank?limit=10"),
    apiGet<Array<Factor & { name?: string }>>("/market/rank?rank_type=score&limit=10"),
  ]);
});
</script>
