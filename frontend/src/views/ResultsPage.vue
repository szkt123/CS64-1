<template>
  <div>
    <el-card class="control-card" style="margin-bottom:16px">
      <template #header>
        <div class="card-header">
          <b>Result Analysis</b>
          <el-tag type="success" effect="plain">Regression + Ranking</el-tag>
        </div>
      </template>

      <el-space wrap>
        <el-input v-model="runIdInput" placeholder="run_id" style="width:240px" />
        <el-input-number
          v-model="rankingMinDiff"
          :min="0"
          :step="0.1"
          :precision="2"
          controls-position="right"
          style="width:180px"
        />
        <span class="hint">ranking_min_diff：Filtering pairs where the manual difference is too small and it is difficult to judge their quality.</span>
        <el-button type="primary" :loading="loading" @click="loadData">Load full analysis</el-button>
      </el-space>
    </el-card>

    <el-alert
      v-if="rankingClaim"
      :title="rankingClaim.title"
      type="success"
      :closable="false"
      show-icon
      style="margin-bottom:16px"
    >
      <template #default>
        <div>
          {{ rankingClaim.text }}
          当前 overall same-paper pairwise accuracy：
          <b>{{ formatPercent(rankingClaim.overall_pairwise_accuracy) }}</b>，
          有效 same-paper pairs：<b>{{ rankingClaim.overall_valid_pairs }}</b>。
        </div>
      </template>
    </el-alert>

    <el-row :gutter="16" v-if="summaryRows.length">
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-title">Macro MAE</div>
          <div class="metric-value">{{ formatNumber(summary.macro_avg?.mae) }}</div>
          <div class="metric-desc">The lower the better</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-title">Macro Spearman</div>
          <div class="metric-value">{{ formatNumber(summary.macro_avg?.spearman) }}</div>
          <div class="metric-desc">Rank relevance, the higher the better</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card ranking">
          <div class="metric-title">Overall Pairwise Accuracy</div>
          <div class="metric-value">{{ formatPercent(pairwiseSummary.overall?.pairwise_accuracy) }}</div>
          <div class="metric-desc">Comparison of two figures from the same paper</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="metric-card ranking">
          <div class="metric-title">Valid Pairwise Pairs</div>
          <div class="metric-value">{{ pairwiseSummary.overall?.valid_pairs || 0 }}</div>
          <div class="metric-desc">Effective pairs after filtering out low differences</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" v-if="summaryRows.length" style="margin-top:16px">
      <el-col :span="8">
        <el-card>
          <template #header><b>Basic indicators: MAE / MSE / Spearman</b></template>
          <LineChart :option="barOption" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><b>Gold vs Pred</b></template>
          <LineChart :option="scatterOption" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><b>Same-paper Pairwise Accuracy</b></template>
          <LineChart :option="pairwiseOption" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px" v-if="crossFocusOption">
      <el-col :span="12">
        <el-card>
          <template #header><b>Cross-Attention Modal Focusing</b></template>
          <LineChart :option="crossFocusOption" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><b>Dominant mode distribution in each dimension</b></template>
          <LineChart :option="topModalityOption" />
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top:16px" v-if="pairwiseRows.length">
      <template #header>
        <div class="card-header">
          <b>Two images in the same article</b>
          <el-tag type="warning" effect="plain">Prove that the model supports ranking comparison</el-tag>
        </div>
      </template>

      <el-space style="margin-bottom:12px" wrap>
        <el-select v-model="selectedPairDim" style="width:220px">
          <el-option label="overall" value="overall" />
          <el-option v-for="d in dims" :key="d" :label="d" :value="d" />
        </el-select>
        <el-switch v-model="onlyWrongPairs" active-text="Only view error pairs" />
      </el-space>

      <el-table :data="filteredPairwiseRows.slice(0, 200)" border height="460">
        <el-table-column prop="paper_id" label="paper_id" width="140" />
        <el-table-column prop="dimension" label="dimension" width="120" />
        <el-table-column prop="figure_a" label="figure A" width="110" />
        <el-table-column prop="figure_b" label="figure B" width="110" />
        <el-table-column prop="human_score_a" label="human A" width="100" />
        <el-table-column prop="human_score_b" label="human B" width="100" />
        <el-table-column prop="pred_score_a" label="pred A" width="100" />
        <el-table-column prop="pred_score_b" label="pred B" width="100" />
        <el-table-column prop="human_winner" label="human winner" width="130" />
        <el-table-column prop="model_winner" label="model winner" width="130" />
        <el-table-column label="correct" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_correct ? 'success' : 'danger'">
              {{ scope.row.is_correct ? 'Yes' : 'No' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="caption_a" label="caption A" min-width="240" show-overflow-tooltip />
        <el-table-column prop="caption_b" label="caption B" min-width="240" show-overflow-tooltip />
      </el-table>
    </el-card>

    <el-card style="margin-top:16px" v-if="tableRows.length">
      <template #header><b>Single Figure Prediction Details</b></template>
      <el-space style="margin-bottom:12px" wrap>
        <el-select v-model="selectedDim" style="width:220px">
          <el-option v-for="d in dims" :key="d" :label="d" :value="d" />
        </el-select>
        <el-select v-model="selectedModality" style="width:220px" v-if="availableModalities.length">
          <el-option v-for="m in availableModalities" :key="m" :label="m" :value="m" />
        </el-select>
      </el-space>
      <el-table :data="tableRows.slice(0,200)" border height="520">
        <el-table-column prop="paper_id" label="paper_id" width="140" />
        <el-table-column prop="figure_id" label="figure_id" width="110" />
        <el-table-column prop="figure_type" label="figure_type" width="140" />
        <el-table-column prop="selected_gold" label="gold" width="90" />
        <el-table-column prop="selected_pred" label="pred" width="90" />
        <el-table-column prop="selected_err" label="err" width="90" />
        <el-table-column prop="top_modality" label="top modality" width="130" />
        <el-table-column prop="top_patch" label="top patch" width="100" />
        <el-table-column prop="caption_text" label="caption" min-width="320" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'
import LineChart from '../components/LineChart.vue'
import { downloadCsv, downloadJson } from '../utils/exportData'

const dims = ['clarity', 'relevance', 'informativeness', 'structure']
const route = useRoute()
const runIdInput = ref(route.params.runId || '')
const rankingMinDiff = ref(0.5)
const loading = ref(false)

const rows = ref([])
const summary = ref({})
const pairwiseSummary = ref({})
const pairwiseRows = ref([])
const rankingClaim = ref(null)

const selectedDim = ref('clarity')
const selectedPairDim = ref('overall')
const selectedModality = ref('caption')
const onlyWrongPairs = ref(false)

const formatNumber = (value) => {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return '-'
  return Number(value).toFixed(4)
}
const formatPercent = (value) => {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

const loadData = async () => {
  if (!runIdInput.value) {
    ElMessage.warning('Please enter run_id')
    return
  }
  loading.value = true
  try {
    const [predRes, sumRes, rankingRes] = await Promise.all([
      api.get(`/runs/${runIdInput.value}/predictions`),
      api.get(`/runs/${runIdInput.value}/summary`),
      api.get(`/ranking/${runIdInput.value}/analysis`, { params: { min_diff: rankingMinDiff.value } }),
    ])
    rows.value = predRes.data || []
    // 使用 ranking endpoint 中增强后的 summary，包含 kendall_tau 和 macro_avg。
    summary.value = rankingRes.data.regression_summary || sumRes.data.summary || {}
    pairwiseSummary.value = rankingRes.data.pairwise_summary || {}
    pairwiseRows.value = rankingRes.data.pairwise_examples || []
    rankingClaim.value = rankingRes.data.claim || null
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || err.message || 'Loading failed')
  } finally {
    loading.value = false
  }
}

if (runIdInput.value) loadData()

const summaryRows = computed(() => dims.map(d => ({ dim: d, ...(summary.value[d] || {}) })))

const tableRows = computed(() => rows.value.map(r => ({
  ...r,
  selected_gold: r.gold_scores?.[selectedDim.value],
  selected_pred: r.pred_scores?.[selectedDim.value],
  selected_err: Number((r.pred_scores?.[selectedDim.value] || 0) - (r.gold_scores?.[selectedDim.value] || 0)).toFixed(3),
  top_modality: r.explanation?.top_modality_per_dimension?.[selectedDim.value] || '-',
  top_patch: r.explanation?.top_patch_index_by_modality?.[selectedModality.value] ?? '-',
})).sort((a, b) => Math.abs(b.selected_err) - Math.abs(a.selected_err)))

const filteredPairwiseRows = computed(() => pairwiseRows.value
  .filter(r => r.dimension === selectedPairDim.value)
  .filter(r => !onlyWrongPairs.value || !r.is_correct))


const resultsExportRows = computed(() => [
  ...summaryRows.value.map(row => ({ chart: 'regression_summary', ...row })),
  ...rows.value.flatMap((r, row_index) => dims.map(dim => ({
    chart: 'scatter_points', row_index, paper_id: r.paper_id, figure_id: r.figure_id, dimension: dim,
    gold: r.gold_scores?.[dim], pred: r.pred_scores?.[dim],
    error: Number(r.pred_scores?.[dim] ?? 0) - Number(r.gold_scores?.[dim] ?? 0),
  }))),
  ...Object.entries(pairwiseSummary.value).map(([dimension, metrics]) => ({ chart: 'pairwise_summary', dimension, ...metrics })),
  ...crossEntries.value.map(([modality, value]) => ({ chart: 'average_cross_modality_focus', modality, value })),
  ...allTopModalities.value.flatMap(modality => dims.map(dim => ({ chart: 'top_modality_counts', dimension: dim, modality, count: topCounts.value[dim]?.[modality] || 0 }))),
])
const exportResultsCsv = () => {
  downloadCsv(`results_visualization_data_${runIdInput.value || 'run'}.csv`, resultsExportRows.value)
  downloadCsv(`pairwise_examples_${runIdInput.value || 'run'}.csv`, pairwiseRows.value)
  downloadCsv(`single_figure_prediction_details_${runIdInput.value || 'run'}.csv`, tableRows.value)
}
const exportResultsJson = () => downloadJson(`results_visualization_data_${runIdInput.value || 'run'}.json`, {
  summary: summary.value,
  pairwise_summary: pairwiseSummary.value,
  pairwise_examples: pairwiseRows.value,
  prediction_rows: rows.value,
  table_rows: tableRows.value,
  chart_rows: resultsExportRows.value,
})

const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['mae', 'mse', 'spearman', 'kendall_tau'] },
  xAxis: { type: 'category', data: summaryRows.value.map(x => x.dim) },
  yAxis: { type: 'value' },
  series: [
    { name: 'mae', type: 'bar', data: summaryRows.value.map(x => x.mae ?? 0) },
    { name: 'mse', type: 'bar', data: summaryRows.value.map(x => x.mse ?? 0) },
    { name: 'spearman', type: 'bar', data: summaryRows.value.map(x => x.spearman ?? 0) },
    { name: 'kendall_tau', type: 'bar', data: summaryRows.value.map(x => x.kendall_tau ?? 0) },
  ],
}))

const scatterOption = computed(() => ({
  tooltip: {},
  xAxis: { type: 'value', name: 'gold' },
  yAxis: { type: 'value', name: 'pred' },
  series: [{
    type: 'scatter',
    data: rows.value.map(r => [r.gold_scores?.[selectedDim.value], r.pred_scores?.[selectedDim.value]]),
  }],
}))

const pairwiseOption = computed(() => {
  const labels = [...dims, 'overall']
  return {
    tooltip: { trigger: 'axis', valueFormatter: v => `${(Number(v) * 100).toFixed(2)}%` },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value', min: 0, max: 1, axisLabel: { formatter: value => `${value * 100}%` } },
    series: [{
      name: 'pairwise_accuracy',
      type: 'bar',
      data: labels.map(k => pairwiseSummary.value[k]?.pairwise_accuracy ?? 0),
      label: { show: true, formatter: p => `${(p.value * 100).toFixed(1)}%` },
    }],
  }
})

const averageMap = (getter) => {
  const acc = {}
  let n = 0
  for (const row of rows.value) {
    const obj = getter(row) || {}
    const keys = Object.keys(obj)
    if (!keys.length) continue
    n += 1
    for (const [k, v] of Object.entries(obj)) acc[k] = (acc[k] || 0) + Number(v || 0)
  }
  return Object.entries(acc).map(([k, v]) => [k, n ? v / n : 0])
}

const crossEntries = computed(() => averageMap(row => row.explanation?.cross_modality_focus))
const crossFocusOption = computed(() => crossEntries.value.length ? ({
  xAxis: { type: 'category', data: crossEntries.value.map(x => x[0]) },
  yAxis: { type: 'value', min: 0, max: 1 },
  series: [{ type: 'bar', data: crossEntries.value.map(x => x[1]) }],
}) : null)

const topCounts = computed(() => {
  const counts = {}
  dims.forEach(dim => { counts[dim] = {} })
  for (const row of rows.value) {
    const tops = row.explanation?.top_modality_per_dimension || {}
    for (const dim of dims) {
      const m = tops[dim]
      if (m) counts[dim][m] = (counts[dim][m] || 0) + 1
    }
  }
  return counts
})
const allTopModalities = computed(() => Array.from(new Set(Object.values(topCounts.value).flatMap(obj => Object.keys(obj)))))
const topModalityOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: allTopModalities.value },
  xAxis: { type: 'category', data: dims },
  yAxis: { type: 'value' },
  series: allTopModalities.value.map(m => ({
    name: m,
    type: 'bar',
    stack: 'total',
    data: dims.map(dim => topCounts.value[dim]?.[m] || 0),
  })),
}))
const availableModalities = computed(() => Array.from(new Set(rows.value.flatMap(row => Object.keys(row.explanation?.cross_attention_patch_focus || {})))))
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.hint {
  color: #6b7280;
  font-size: 13px;
}
.metric-card {
  min-height: 120px;
}
.metric-card.ranking {
  border: 1px solid #f5d68a;
}
.metric-title {
  color: #6b7280;
  font-size: 13px;
  margin-bottom: 8px;
}
.metric-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}
.metric-desc {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
</style>
