<template>
  <div>
    <el-card>
      <template #header><b>Batch test set prediction</b></template>
      <el-alert
        title="Used to generate prediction results in batches from test.jsonl. The results are saved by default to output_dir/test_predictions.jsonl."
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      />
      <el-form :model="form" label-width="160px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="Checkpoint"><el-input v-model="form.checkpoint" placeholder="For example: ./runs/run1/best.pt" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="Test JSONL"><el-input v-model="form.input_jsonl" placeholder="For example: ./data/splits/test.jsonl" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="Output Dir"><el-input v-model="form.output_dir" placeholder="For example: ./runs/run1" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="Output Filename"><el-input v-model="form.output_filename" placeholder="For example: test_predictions.jsonl" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Batch Size"><el-input-number v-model="form.batch_size" :min="1" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Num Workers"><el-input-number v-model="form.num_workers" :min="0" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="Device">
            <el-select v-model="form.device" style="width:100%">
              <el-option label="auto" value="auto" />
              <el-option label="cuda" value="cuda" />
              <el-option label="cpu" value="cpu" />
              <el-option label="mps" value="mps" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
        <el-space wrap>
          <el-checkbox v-model="form.verify_images">verify_images</el-checkbox>
          <el-checkbox v-model="form.include_weak_labels">include_weak_labels</el-checkbox>
        </el-space>
        <div style="margin-top:16px">
          <el-button type="primary" :loading="starting" @click="startPredict">Start Test Predict</el-button>
          <el-button @click="connectWs" :disabled="!runId">Connect to monitoring</el-button>
          <el-button @click="loadPredictions" :disabled="!runId">Read results</el-button>
          <el-button type="success" @click="goResults" :disabled="!runId">Go to Results Analysis Page</el-button>
        </div>
      </el-form>
    </el-card>

    <el-card v-if="runId" style="margin-top:16px">
      <template #header><b>Task monitoring</b></template>
      <el-row :gutter="12">
        <el-col :span="6"><el-statistic title="Run ID" :value="runId" /></el-col>
        <el-col :span="6"><el-statistic title="state" :value="status.status || '-'" /></el-col>
        <el-col :span="6"><el-statistic title="Output directory" :value="status.output_dir || '-'" /></el-col>
        <el-col :span="6"><el-statistic title="Current Epoch" :value="`${status.current_epoch || 0}/${status.total_epochs || 0}`" /></el-col>
      </el-row>
      <div style="margin-top:12px">
        <div class="subtle-text">Overall progress</div>
        <el-progress :percentage="progressPercent" :status="progressStatus" :stroke-width="16" />
      </div>
    </el-card>

    <el-card v-if="runId" style="margin-top:16px">
      <template #header><b>Real-time logs</b></template>
      <div class="log-panel" style="max-height:320px;overflow:auto;background:#0f172a;color:#e2e8f0;padding:12px;border-radius:8px">
        <div v-for="(line, idx) in logs" :key="idx" style="font-family:monospace;font-size:12px;line-height:1.7">{{ line }}</div>
      </div>
    </el-card>

    <el-card v-if="rows.length" style="margin-top:16px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px">
          <b>Prediction results preview</b>
          <el-tag type="success">{{ rows.length }} rows</el-tag>
        </div>
      </template>
      <el-table :data="rows.slice(0, 50)" border style="width:100%">
        <el-table-column prop="paper_id" label="paper_id" min-width="140" />
        <el-table-column prop="figure_id" label="figure_id" min-width="140" />
        <el-table-column prop="figure_type" label="figure_type" min-width="120" />
        <el-table-column label="clarity" min-width="100">
          <template #default="scope">{{ formatScore(scope.row.pred_scores?.clarity) }}</template>
        </el-table-column>
        <el-table-column label="relevance" min-width="100">
          <template #default="scope">{{ formatScore(scope.row.pred_scores?.relevance) }}</template>
        </el-table-column>
        <el-table-column label="informativeness" min-width="130">
          <template #default="scope">{{ formatScore(scope.row.pred_scores?.informativeness) }}</template>
        </el-table-column>
        <el-table-column label="structure" min-width="100">
          <template #default="scope">{{ formatScore(scope.row.pred_scores?.structure) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'

const route = useRoute()
const router = useRouter()
const runId = ref(route.params.runId || '')
const starting = ref(false)
const status = reactive({})
const logs = ref([])
const rows = ref([])
let ws = null

const form = reactive({
  checkpoint: './runs/run1/best.pt',
  input_jsonl: './data/splits/test.jsonl',
  output_dir: './runs/run1',
  output_filename: 'test_predictions.jsonl',
  batch_size: 4,
  num_workers: 0,
  verify_images: true,
  include_weak_labels: false,
  device: 'auto',
})

const progressPercent = computed(() => {
  const totalEpochs = Number(status.total_epochs || 0)
  const totalSteps = Number(status.total_steps || 0)
  const currentEpoch = Number(status.current_epoch || 0)
  const currentStep = Number(status.current_step || 0)
  if (!totalEpochs) return status.status === 'finished' ? 100 : 0
  const percent = totalSteps
    ? (((Math.max(0, currentEpoch - 1) * totalSteps + currentStep) / Math.max(totalEpochs * totalSteps, 1)) * 100)
    : ((currentEpoch / totalEpochs) * 100)
  return Number(Math.min(100, Math.max(0, percent)).toFixed(1))
})
const progressStatus = computed(() => status.status === 'failed' ? 'exception' : (status.status === 'finished' ? 'success' : undefined))

const closeWs = () => {
  if (ws) {
    ws.close()
    ws = null
  }
}

const connectWs = () => {
  if (!runId.value) return
  closeWs()
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${protocol}://${location.host}/api/train/ws/${runId.value}`)
  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data)
    if (msg.type === 'status') {
      Object.assign(status, msg)
      logs.value = msg.logs || []
      if (['finished', 'failed', 'stopped'].includes(msg.status)) {
        loadPredictions()
      }
    }
  }
  ws.onerror = () => ElMessage.error('WebSocket connection failed.')
}

const startPredict = async () => {
  starting.value = true
  rows.value = []
  try {
    const { data } = await api.post('/infer/start-test-predict', form)
    runId.value = data.run_id
    router.replace(`/test-predict/${data.run_id}`)
    ElMessage.success('Test Predict has been started.')
    connectWs()
  } catch (err) {
    const detail = err?.response?.data?.detail || 'Startup failed'
    ElMessage.error(String(detail))
  } finally {
    starting.value = false
  }
}

const loadPredictions = async () => {
  if (!runId.value) return
  try {
    const { data } = await api.get(`/runs/${runId.value}/predictions`)
    rows.value = data || []
    if (rows.value.length) ElMessage.success(`${rows.value.length} prediction results have been read.`)
  } catch (err) {
    const detail = err?.response?.data?.detail || 'Failed to read prediction results'
    ElMessage.error(String(detail))
  }
}

const goResults = () => {
  if (!runId.value) return
  router.push(`/results/${runId.value}`)
}

const formatScore = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n.toFixed(4) : '-'
}

if (runId.value) connectWs()

onBeforeUnmount(() => closeWs())
</script>
