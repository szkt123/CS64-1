<template>
  <div>
    <el-card style="margin-bottom:16px">
      <template #header><b>Training monitoring</b></template>
      <div class="toolbar-row">
        <el-space wrap>
          <el-input v-model="runIdInput" placeholder="run_id" style="width:240px" />
          <el-button type="primary" @click="connectWs">connect</el-button>
          <el-button @click="refreshHistory" :disabled="!runId">Breaking History</el-button>
          <el-button type="danger" @click="stopRun" :disabled="!runId">Stop training</el-button><el-button @click="exportTrainingCsv" :disabled="!batchHistory.length && !epochHistory.length">Export CSV</el-button><el-button @click="exportTrainingJson" :disabled="!batchHistory.length && !epochHistory.length">Export JSON</el-button>
        </el-space>
        <el-space wrap>
          <span class="toolbar-label">Smooth Window</span>
          <el-slider v-model="smoothWindow" :min="1" :max="50" :step="1" style="width:220px" />
          <el-tag type="info">{{ smoothWindow }}</el-tag>
        </el-space>
      </div>

      <el-row :gutter="12" style="margin-top:16px">
        <el-col :span="4"><el-statistic title="state" :value="status.status || '-'" /></el-col>
        <el-col :span="4"><el-statistic title="Current Epoch" :value="epochText" /></el-col>
        <el-col :span="4"><el-statistic title="Current Step" :value="stepText" /></el-col>
        <el-col :span="4"><el-statistic title="Train Loss" :value="displayNumber(status.train_loss)" /></el-col>
        <el-col :span="4"><el-statistic title="Val Loss" :value="displayNumber(status.val_loss)" /></el-col>
        <el-col :span="4"><el-statistic title="Best Val Loss" :value="displayNumber(status.best_val)" /></el-col>
      </el-row>

      <div style="margin-top:12px">
        <div class="subtle-text">Overall training progress</div>
        <el-progress :percentage="progressPercent" :status="progressStatus" :stroke-width="16" />
      </div>
      <div style="margin-top:12px">
        <div class="subtle-text">Current Epoch Progress</div>
        <el-progress :percentage="epochProgressPercent" :stroke-width="12" />
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12"><el-card><template #header><div class="card-header"><b>Real-time Loss Curve</b><el-tag size="small">{{ batchHistory.length }} points</el-tag></div></template><LineChart :option="lossOption" /></el-card></el-col>
      <el-col :span="12"><el-card><template #header><div class="card-header"><b>Epoch Loss + Spearman</b><el-tag size="small">{{ epochHistory.length }} epochs</el-tag></div></template><LineChart :option="metricOption" /></el-card></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12"><el-card><template #header><b>Cross-Attention Training Statistics</b></template><LineChart :option="attentionBatchOption" /></el-card></el-col>
      <el-col :span="12"><el-card><template #header><b>Cross-Attention Epoch Summary</b></template><LineChart :option="attentionEpochOption" /></el-card></el-col>
    </el-row>

    <el-card style="margin-top:16px">
      <template #header><div class="card-header"><b>Real-time logs</b><el-space><el-tag size="small">{{ logs.length }} lines</el-tag><el-switch v-model="autoScroll" active-text="Automatic scrolling" /><el-button size="small" @click="copyLogs">Copy log</el-button><el-button size="small" @click="clearLogsView">Clear display</el-button></el-space></div></template>
      <div ref="logContainer" class="log-panel"><div v-for="(line, idx) in logs" :key="idx" :class="logClass(line)">{{ line }}</div></div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'
import LineChart from '../components/LineChart.vue'
import { downloadCsv, downloadJson } from '../utils/exportData'

const route = useRoute()
const runId = ref(route.params.runId || '')
const runIdInput = ref(runId.value)
const logs = ref([])
const batchHistory = ref([])
const epochHistory = ref([])
const smoothWindow = ref(10)
const autoScroll = ref(true)
const status = reactive({})
const logContainer = ref(null)
let ws = null
const DISPLAY_DIMS = ['clarity', 'relevance', 'informativeness', 'structure']
const displayNumber = (value) => { const num = Number(value); return Number.isFinite(num) ? num.toFixed(4) : '-' }
const toNumberOrNull = (value) => { const num = Number(value); return Number.isFinite(num) ? num : null }
const movingAverage = (arr, key, windowSize) => { const values = arr.map(item => toNumberOrNull(item?.[key])); const result = []; let sum = 0; let count = 0; const queue = []; for (const value of values) { queue.push(value); if (value !== null) { sum += value; count += 1 } if (queue.length > windowSize) { const removed = queue.shift(); if (removed !== null) { sum -= removed; count -= 1 } } result.push(count > 0 ? Number((sum / count).toFixed(6)) : null) } return result }
const epochText = computed(() => `${status.current_epoch || 0}/${status.total_epochs || 0}`)
const stepText = computed(() => `${status.current_step || 0}/${status.total_steps || 0}`)
const progressPercent = computed(() => { const totalEpochs = Number(status.total_epochs || 0); const totalSteps = Number(status.total_steps || 0); const currentEpoch = Number(status.current_epoch || 0); const currentStep = Number(status.current_step || 0); if (!totalEpochs) return 0; const percent = totalSteps ? (((Math.max(0, currentEpoch - 1) * totalSteps + currentStep) / Math.max(totalEpochs * totalSteps, 1)) * 100) : ((currentEpoch / totalEpochs) * 100); return Number(Math.min(100, Math.max(0, percent)).toFixed(1)) })
const progressStatus = computed(() => status.status === 'failed' ? 'exception' : (status.status === 'finished' ? 'success' : undefined))
const epochProgressPercent = computed(() => { const totalSteps = Number(status.total_steps || 0); const currentStep = Number(status.current_step || 0); if (!totalSteps) return 0; return Number(Math.min(100, Math.max(0, (currentStep / totalSteps) * 100)).toFixed(1)) })
const scrollLogsToBottom = async () => { if (!autoScroll.value) return; await nextTick(); if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight }
watch(logs, scrollLogsToBottom, { deep: true })
const applyPayload = (data) => { Object.assign(status, data); logs.value = Array.isArray(data.logs) ? data.logs : []; batchHistory.value = Array.isArray(data.batch_history) ? data.batch_history : []; epochHistory.value = Array.isArray(data.epoch_history) ? data.epoch_history : [] }
const refreshHistory = async () => { if (!runId.value) return; const res = await api.get(`/train/status/${runId.value}`); applyPayload(res.data) }
const connectWs = async () => { if (ws) ws.close(); runId.value = runIdInput.value.trim(); if (!runId.value) return; await refreshHistory(); const protocol = location.protocol === 'https:' ? 'wss' : 'ws'; ws = new WebSocket(`${protocol}://${location.host}/api/train/ws/${runId.value}`); ws.onmessage = (event) => applyPayload(JSON.parse(event.data)); ws.onerror = () => ElMessage.error('WebSocket 连接失败') }
const stopRun = async () => { if (!runId.value) return; await api.post(`/train/stop/${runId.value}`); ElMessage.success('Stop request sent') }
const clearLogsView = () => { logs.value = [] }
const copyLogs = async () => { try { await navigator.clipboard.writeText(logs.value.join('\n')); ElMessage.success('Log has been copied') } catch { ElMessage.error('Copy failed') } }
const logClass = (line) => { const lower = String(line).toLowerCase(); if (lower.includes('[warning]')) return 'log-warning'; if (lower.includes('[done]')) return 'log-success'; if (lower.includes('[checkpoint]')) return 'log-info'; if (lower.includes('error') || lower.includes('failed') || lower.includes('traceback')) return 'log-error'; return 'log-normal' }
const lossXAxis = computed(() => batchHistory.value.map(item => item.global_step ?? 0))
const epochXAxis = computed(() => epochHistory.value.map(item => item.epoch))
const lossOption = computed(() => ({ animation: false, tooltip: { trigger: 'axis' }, legend: { top: 4, data: ['loss', 'reg_loss', 'rank_loss'] }, grid: { left: 56, right: 28, top: 44, bottom: 60 }, dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 12, height: 18 }], xAxis: { type: 'category', boundaryGap: false, data: lossXAxis.value, name: 'global step' }, yAxis: { type: 'value', scale: true, name: 'loss' }, series: [{ name: 'loss', type: 'line', smooth: 0.25, showSymbol: false, data: movingAverage(batchHistory.value, 'loss', smoothWindow.value) }, { name: 'reg_loss', type: 'line', smooth: 0.25, showSymbol: false, data: movingAverage(batchHistory.value, 'reg_loss', smoothWindow.value) }, { name: 'rank_loss', type: 'line', smooth: 0.25, showSymbol: false, data: movingAverage(batchHistory.value, 'rank_loss', smoothWindow.value) }] }))
const metricOption = computed(() => ({ animation: false, tooltip: { trigger: 'axis' }, legend: { top: 4, data: ['train_loss', 'val_loss', ...DISPLAY_DIMS] }, grid: { left: 56, right: 56, top: 44, bottom: 40 }, xAxis: { type: 'category', boundaryGap: false, name: 'epoch', data: epochXAxis.value }, yAxis: [{ type: 'value', name: 'loss', scale: true }, { type: 'value', name: 'spearman', min: -1, max: 1 }], series: [{ name: 'train_loss', type: 'line', yAxisIndex: 0, smooth: true, data: epochHistory.value.map(x => toNumberOrNull(x.train_loss)) }, { name: 'val_loss', type: 'line', yAxisIndex: 0, smooth: true, data: epochHistory.value.map(x => toNumberOrNull(x.val_loss)) }, ...DISPLAY_DIMS.map(dim => ({ name: dim, type: 'line', yAxisIndex: 1, smooth: true, connectNulls: true, data: epochHistory.value.map(x => toNumberOrNull(x.val_metrics?.[dim]?.spearman ?? x.metric_snapshot?.[dim])) }))] }))
const attentionBatchOption = computed(() => ({ animation: false, tooltip: { trigger: 'axis' }, legend: { top: 4, data: ['attn_peak','attn_entropy'] }, grid: { left: 56, right: 32, top: 44, bottom: 50 }, xAxis: { type: 'category', boundaryGap: false, data: lossXAxis.value, name: 'global step' }, yAxis: [{ type: 'value', name: 'peak', min: 0, max: 1 }, { type: 'value', name: 'entropy', scale: true }], series: [{ name: 'attn_peak', type: 'line', smooth: true, showSymbol: false, yAxisIndex: 0, data: movingAverage(batchHistory.value, 'attn_peak', smoothWindow.value) }, { name: 'attn_entropy', type: 'line', smooth: true, showSymbol: false, yAxisIndex: 1, data: movingAverage(batchHistory.value, 'attn_entropy', smoothWindow.value) }] }))

const metricRowsForExport = computed(() => epochHistory.value.flatMap(item => DISPLAY_DIMS.map(dim => ({
  epoch: item.epoch,
  dimension: dim,
  train_loss: item.train_loss,
  val_loss: item.val_loss,
  spearman: item.val_metrics?.[dim]?.spearman ?? item.metric_snapshot?.[dim]?.spearman ?? item.metric_snapshot?.[dim],
  mae: item.val_metrics?.[dim]?.mae ?? item.metric_snapshot?.[dim]?.mae,
}))))
const exportTrainingCsv = () => {
  downloadCsv(`training_batch_history_${runId.value || 'run'}.csv`, batchHistory.value)
  downloadCsv(`training_epoch_metrics_${runId.value || 'run'}.csv`, metricRowsForExport.value)
}
const exportTrainingJson = () => downloadJson(`training_visualization_data_${runId.value || 'run'}.json`, {
  status,
  batch_history: batchHistory.value,
  epoch_history: epochHistory.value,
  epoch_metric_rows: metricRowsForExport.value,
})

const attentionEpochOption = computed(() => ({ animation: false, tooltip: { trigger: 'axis' }, legend: { top: 4, data: ['attn_peak','attn_entropy'] }, grid: { left: 56, right: 32, top: 44, bottom: 40 }, xAxis: { type: 'category', boundaryGap: false, data: epochXAxis.value, name: 'epoch' }, yAxis: [{ type: 'value', name: 'peak', min: 0, max: 1 }, { type: 'value', name: 'entropy', scale: true }], series: [{ name: 'attn_peak', type: 'line', smooth: true, yAxisIndex: 0, data: epochHistory.value.map(x => toNumberOrNull(x.attn_peak)) }, { name: 'attn_entropy', type: 'line', smooth: true, yAxisIndex: 1, data: epochHistory.value.map(x => toNumberOrNull(x.attn_entropy)) }] }))
if (runId.value) connectWs()
onBeforeUnmount(() => { if (ws) ws.close() })
</script>

<style scoped>
.toolbar-row{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.toolbar-label{color:#475569;font-size:14px}.subtle-text{color:#64748b;font-size:13px;margin-bottom:6px}.card-header{display:flex;align-items:center;justify-content:space-between}.log-panel{background:#0f172a;color:#e2e8f0;padding:12px;border-radius:10px;height:320px;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;line-height:1.5}.log-normal{color:#e2e8f0}.log-warning{color:#fbbf24}.log-error{color:#f87171}.log-success{color:#4ade80}.log-info{color:#60a5fa}
</style>
