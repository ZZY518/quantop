<template>
  <div class="page">
    <section class="section">
      <h1>同步任务</h1>
      <div class="actions">
        <label class="field">
          <span>数据源</span>
          <select v-model="dataSource" :disabled="isSyncBlocked || switchingSource" @change="switchDataSource">
            <option v-for="option in dataSourceOptions" :key="option" :value="option">
              {{ dataSourceLabel(option) }}
            </option>
          </select>
        </label>
        <label class="field">
          <span>同步数量</span>
          <input v-model.number="syncLimit" type="number" min="1" max="500" step="1" :disabled="isSyncBlocked" />
        </label>
        <button @click="runSync" :disabled="isSyncBlocked">
          {{ isSyncBlocked ? "同步中" : "同步数据" }}
        </button>
        <button class="secondary" @click="loadLogs" :disabled="loadingLogs">
          {{ loadingLogs ? "刷新中" : "刷新日志" }}
        </button>
      </div>
      <p class="muted" v-if="message">{{ message }}</p>
      <p class="error" v-if="error">{{ error }}</p>
    </section>

    <section class="section">
      <h2>同步日志</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>任务</th>
              <th>来源</th>
              <th>状态</th>
              <th>业务日期</th>
              <th>总数</th>
              <th>成功</th>
              <th>失败</th>
              <th>开始时间</th>
              <th>错误</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id">
              <td>{{ log.id }}</td>
              <td>{{ log.task_name }}</td>
              <td>{{ log.source }}</td>
              <td>
                <span :class="{ running: log.status === 'running' }">{{ log.status }}</span>
              </td>
              <td>{{ log.biz_date || "-" }}</td>
              <td>{{ log.total_count }}</td>
              <td>{{ log.success_count }}</td>
              <td>{{ log.fail_count }}</td>
              <td>{{ log.start_time }}</td>
              <td>{{ log.id === activeLogId && log.status === "running" ? "同步未完成，请等待" : log.error_message || "-" }}</td>
            </tr>
            <tr v-if="logs.length === 0">
              <td colspan="10" class="muted">暂无同步日志。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { apiGet, apiPost, type DataSourceSettings, type SyncLog } from "@/lib/api";

const logs = ref<SyncLog[]>([]);
const message = ref("");
const error = ref("");
const running = ref(false);
const loadingLogs = ref(false);
const syncLimit = ref(10);
const dataSource = ref("akshare");
const dataSourceOptions = ref<string[]>(["akshare", "baostock"]);
const switchingSource = ref(false);
const activeLogId = ref<number | null>(null);
let pollTimer: number | undefined;

const isSyncBlocked = computed(() => running.value || activeLogId.value !== null);

async function loadDataSource() {
  const settings = await apiGet<DataSourceSettings>("/settings/data-source");
  dataSource.value = settings.current;
  dataSourceOptions.value = settings.options;
}

async function switchDataSource() {
  switchingSource.value = true;
  error.value = "";
  try {
    const settings = await apiPost<DataSourceSettings>(`/settings/data-source?source=${dataSource.value}`);
    dataSource.value = settings.current;
    dataSourceOptions.value = settings.options;
    message.value = `已切换到 ${dataSourceLabel(settings.current)}`;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "切换数据源失败";
    await loadDataSource();
  } finally {
    switchingSource.value = false;
  }
}

async function loadLogs() {
  loadingLogs.value = true;
  error.value = "";
  try {
    logs.value = await apiGet<SyncLog[]>("/sync/logs");
    updateActiveLog();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载同步日志失败";
  } finally {
    loadingLogs.value = false;
  }
}

async function runSync() {
  if (isSyncBlocked.value) return;
  const limit = normalizeLimit(syncLimit.value);
  syncLimit.value = limit;
  running.value = true;
  message.value = `执行中，本次同步 ${limit} 只股票`;
  error.value = "";
  try {
    const log = await apiPost<SyncLog>(`/sync/run?limit=${limit}`);
    activeLogId.value = log.status === "running" ? log.id : null;
    message.value = log.status === "running" ? `同步任务已启动，日志 ID ${log.id}` : `${log.task_name} ${log.status}，成功 ${log.success_count} 条`;
    await loadLogs();
    startPolling();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "同步任务执行失败";
    message.value = "";
  } finally {
    running.value = false;
  }
}

function updateActiveLog() {
  const runningLog = logs.value.find((log) => log.status === "running");
  activeLogId.value = runningLog?.id ?? null;
  if (activeLogId.value === null) {
    stopPolling();
    if (running.value) message.value = "同步已结束";
  }
}

function startPolling() {
  if (pollTimer !== undefined || activeLogId.value === null) return;
  pollTimer = window.setInterval(loadLogs, 2000);
}

function stopPolling() {
  if (pollTimer === undefined) return;
  window.clearInterval(pollTimer);
  pollTimer = undefined;
}

function normalizeLimit(value: number) {
  if (!Number.isFinite(value)) return 10;
  return Math.min(500, Math.max(1, Math.floor(value)));
}

function dataSourceLabel(value: string) {
  if (value === "akshare") return "AKShare";
  if (value === "baostock") return "Baostock";
  return value;
}

onMounted(async () => {
  await Promise.all([loadDataSource(), loadLogs()]);
  startPolling();
});

onBeforeUnmount(stopPolling);
</script>
