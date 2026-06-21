import { createRouter, createWebHistory } from "vue-router";
import HomeView from "@/views/HomeView.vue";
import MarketView from "@/views/MarketView.vue";
import HotRankView from "@/views/HotRankView.vue";
import StockView from "@/views/StockView.vue";
import FactorsView from "@/views/FactorsView.vue";
import SyncView from "@/views/SyncView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: HomeView },
    { path: "/market", component: MarketView },
    { path: "/hot-rank", component: HotRankView },
    { path: "/stock/:symbol", component: StockView, props: true },
    { path: "/factors", component: FactorsView },
    { path: "/sync", component: SyncView },
  ],
});

export default router;
