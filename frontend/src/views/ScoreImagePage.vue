<template>
  <div class="page">
    <el-card class="main-card">
      <template #header>
        <div class="header-row">
          <div>
            <b>Single image scoring</b>
            <div class="sub-title">Predict multidimensional quality scores for one scientific figure</div>
          </div>
          <el-tag type="primary" effect="plain">Single Figure</el-tag>
        </div>
      </template>

      <el-alert
        title="Please enter the path to the best.pt file generated after training, for example, ./runs/run1/best.pt"
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      />

      <el-form label-width="120px">
        <el-form-item label="Checkpoint">
          <el-input
            v-model="checkpoint"
            size="large"
            placeholder="For example: ./runs/run1/best.pt"
          />
        </el-form-item>

        <el-form-item label="Caption">
          <el-input
            v-model="caption_text"
            type="textarea"
            size="large"
            :rows="5"
            placeholder="Enter figure caption"
          />
        </el-form-item>

        <el-form-item label="Context">
          <el-input
            v-model="context_text"
            type="textarea"
            size="large"
            :rows="5"
            placeholder="Enter surrounding context"
          />
        </el-form-item>

        <el-form-item label="Abstract">
          <el-input
            v-model="abstract_text"
            type="textarea"
            size="large"
            :rows="4"
            placeholder="Enter abstract text"
          />
        </el-form-item>

        <el-form-item label="Meta">
          <el-input
            v-model="meta_text"
            type="textarea"
            size="large"
            :rows="4"
            placeholder="Enter metadata"
          />
        </el-form-item>

        <el-form-item label="Image">
          <input type="file" accept="image/*" @change="onFile" />
        </el-form-item>

        <div v-if="preview" class="preview-wrapper">
          <img :src="preview" class="preview" />
        </div>

        <div class="action-row">
          <el-button type="primary" size="large" @click="submit" :disabled="!file">
            Scoring
          </el-button>
        </div>
      </el-form>
    </el-card>

    <el-row :gutter="16" style="margin-top:16px" v-if="scores.length">
      <el-col :xs="24" :md="12">
        <el-card class="chart-card">
          <template #header><b>Predicted score</b></template>
          <el-button size="small" style="margin-bottom:8px" @click="exportSingleImageData">Export CSV/JSON</el-button>
          <LineChart :option="scoreOption" />
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card class="chart-card">
          <template #header><b>Global Modal Contribution</b></template>
          <LineChart :option="modalityOption" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px" v-if="hasCross">
      <el-col :xs="24" :md="12">
        <el-card class="chart-card">
          <template #header><b>Cross-Attention Modal Focusing</b></template>
          <LineChart :option="crossFocusOption" />
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card class="chart-card">
          <template #header><b>Patch Focus (Selected Modality)</b></template>
          <el-select v-model="selectedModality" size="large" style="width:200px;margin-bottom:12px">
            <el-option
              v-for="m in crossModalities"
              :key="m"
              :label="m"
              :value="m"
            />
          </el-select>
          <LineChart :option="patchOption" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import LineChart from '../components/LineChart.vue'
import { downloadCsv, downloadJson } from '../utils/exportData'

const checkpoint = ref('./runs/run1/best.pt')
const caption_text = ref('')
const context_text = ref('')
const abstract_text = ref('')
const meta_text = ref('')
const file = ref(null)
const preview = ref('')

const explanation = ref({})
const scores = ref([])

const dims = ['clarity', 'relevance', 'informativeness', 'structure']
const selectedModality = ref('caption')

const onFile = (e) => {
  file.value = e.target.files?.[0] || null

  if (preview.value) {
    URL.revokeObjectURL(preview.value)
  }

  preview.value = file.value ? URL.createObjectURL(file.value) : ''
}

const submit = async () => {
  try {
    const form = new FormData()
    form.append('checkpoint', checkpoint.value)
    form.append('caption_text', caption_text.value)
    form.append('context_text', context_text.value)
    form.append('abstract_text', abstract_text.value)
    form.append('meta_text', meta_text.value)
    form.append('image', file.value)

    const { data } = await axios.post('/api/infer/score-image', form)

    scores.value = dims.map(d => ({
      dim: d,
      value: data.scores[d],
    }))

    explanation.value = data.explanation || {}
  } catch (err) {
    const detail = err?.response?.data?.detail || '打分失败'
    ElMessage.error(String(detail))
  }
}


const singleImageExportRows = computed(() => [
  ...scores.value.map(row => ({ chart: 'predicted_score', dimension: row.dim, value: row.value })),
  ...modalityEntries.value.map(([modality, value]) => ({ chart: 'global_modality_importance', modality, value })),
  ...crossFocusEntries.value.map(([modality, value]) => ({ chart: 'cross_modality_focus', modality, value })),
  ...crossModalities.value.flatMap(modality => (explanation.value.cross_attention_patch_focus?.[modality] || []).map((value, patch_index) => ({ chart: 'patch_focus', modality, patch_index, value }))),
])
const exportSingleImageData = () => {
  downloadCsv('single_image_visualization_data.csv', singleImageExportRows.value)
  downloadJson('single_image_visualization_data.json', {
    scores: scores.value,
    explanation: explanation.value,
    rows: singleImageExportRows.value,
  })
}

const scoreOption = computed(() => ({
  xAxis: {
    type: 'category',
    data: scores.value.map(x => x.dim),
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 5,
  },
  series: [
    {
      type: 'bar',
      data: scores.value.map(x => x.value),
    },
  ],
}))

const modalityEntries = computed(() =>
  Object.entries(explanation.value.global_modality_importance || {})
)

const modalityOption = computed(() => ({
  xAxis: {
    type: 'category',
    data: modalityEntries.value.map(x => x[0]),
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 1,
  },
  series: [
    {
      type: 'bar',
      data: modalityEntries.value.map(x => x[1]),
    },
  ],
}))

const crossModalities = computed(() =>
  Object.keys(explanation.value.cross_attention_patch_focus || {})
)

const hasCross = computed(() => crossModalities.value.length > 0)

const crossFocusEntries = computed(() =>
  Object.entries(explanation.value.cross_modality_focus || {})
)

const crossFocusOption = computed(() => ({
  xAxis: {
    type: 'category',
    data: crossFocusEntries.value.map(x => x[0]),
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 1,
  },
  series: [
    {
      type: 'bar',
      data: crossFocusEntries.value.map(x => x[1]),
    },
  ],
}))

const patchSeries = computed(() =>
  explanation.value.cross_attention_patch_focus?.[selectedModality.value] || []
)

const patchOption = computed(() => ({
  xAxis: {
    type: 'category',
    data: patchSeries.value.map((_, idx) => idx),
  },
  yAxis: {
    type: 'value',
    min: 0,
  },
  series: [
    {
      type: 'line',
      smooth: true,
      data: patchSeries.value,
    },
  ],
}))
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.main-card,
.chart-card {
  border-radius: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sub-title {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
}

.preview-wrapper {
  margin-top: 10px;
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}

.preview {
  width: 100%;
  max-height: 420px;
  object-fit: contain;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #f8fafc;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.action-row {
  margin-top: 16px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

:deep(.el-textarea__inner) {
  font-size: 15px;
  padding: 14px;
  line-height: 1.6;
}

:deep(.el-input__inner) {
  height: 44px;
  font-size: 15px;
}
</style>