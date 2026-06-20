<template>
  <div class="page">
    <section class="section">
      <h1>因子评分排行</h1>
      <RankTable :rows="rank" mode="score" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import RankTable from "@/components/RankTable.vue";
import { apiGet, type Factor } from "@/lib/api";

const rank = ref<Array<Factor & { name?: string }>>([]);

onMounted(async () => {
  rank.value = await apiGet<Array<Factor & { name?: string }>>("/market/rank?rank_type=score&limit=50");
});
</script>
