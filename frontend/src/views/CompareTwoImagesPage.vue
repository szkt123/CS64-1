<template>
  <div class="page">
    <el-card class="main-card">
      <template #header>
        <div class="header-row">
          <div>
            <b>Comparison of two images</b>
            <div class="sub-title">Compare two scientific figures with the trained model</div>
          </div>
          <el-tag type="success" effect="plain">Ranking Capability</el-tag>
        </div>
      </template>

      <el-alert
        title="This page is used to verify the model's comparative ability: predict multidimensional quality scores for two images respectively, then compare the overall scores to determine which image the model considers to be of higher quality."
        type="info"
        :closable="false"
        style="margin-bottom: 16px"
      />

      <el-form label-width="130px">
        <el-form-item label="Checkpoint">
          <el-input
            v-model="checkpoint"
            size="large"
            placeholder="For example: ./runs/run1/best.pt"
          />
        </el-form-item>

        <el-row :gutter="18">
          <el-col :xs="24" :md="12">
            <el-card shadow="never" class="image-card">
              <template #header><b>Figure A</b></template>

              <el-form-item label="Figure ID" label-width="90px">
                <el-input
                  v-model="figureA.figure_id"
                  size="large"
                  placeholder="For example: Fig. 1"
                />
              </el-form-item>

              <el-form-item label="Caption" label-width="90px">
                <el-input
                  v-model="figureA.caption_text"
                  type="textarea"
                  size="large"
                  :rows="5"
                />
              </el-form-item>

              <el-form-item label="Context" label-width="90px">
                <el-input
                  v-model="figureA.context_text"
                  type="textarea"
                  size="large"
                  :rows="5"
                />
              </el-form-item>

              <el-form-item label="Abstract" label-width="90px">
                <el-input
                  v-model="figureA.abstract_text"
                  type="textarea"
                  size="large"
                  :rows="4"
                />
              </el-form-item>

              <el-form-item label="Meta" label-width="90px">
                <el-input
                  v-model="figureA.meta_text"
                  type="textarea"
                  size="large"
                  :rows="4"
                />
              </el-form-item>

              <el-form-item label="Image" label-width="90px">
                <input type="file" accept="image/*" @change="onFileA" />
              </el-form-item>

              <div v-if="previewA" class="preview-wrapper">
                <img :src="previewA" class="preview" />
              </div>
            </el-card>
          </el-col>

          <el-col :xs="24" :md="12">
            <el-card shadow="never" class="image-card">
              <template #header><b>Figure B</b></template>

              <el-form-item label="Figure ID" label-width="90px">
                <el-input
                  v-model="figureB.figure_id"
                  size="large"
                  placeholder="For example: Fig. 2"
                />
              </el-form-item>

              <el-form-item label="Caption" label-width="90px">
                <el-input
                  v-model="figureB.caption_text"
                  type="textarea"
                  size="large"
                  :rows="5"
                />
              </el-form-item>

              <el-form-item label="Context" label-width="90px">
                <el-input
                  v-model="figureB.context_text"
                  type="textarea"
                  size="large"
                  :rows="5"
                />
              </el-form-item>

              <el-form-item label="Abstract" label-width="90px">
                <el-input
                  v-model="figureB.abstract_text"
                  type="textarea"
                  size="large"
                  :rows="4"
                />
              </el-form-item>

              <el-form-item label="Meta" label-width="90px">
                <el-input
                  v-model="figureB.meta_text"
                  type="textarea"
                  size="large"
                  :rows="4"
                />
              </el-form-item>

              <el-form-item label="Image" label-width="90px">
                <input type="file" accept="image/*" @change="onFileB" />
              </el-form-item>

              <div v-if="previewB" class="preview-wrapper">
                <img :src="previewB" class="preview" />
              </div>
            </el-card>
          </el-col>
        </el-row>

        <div class="action-row">
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            :disabled="!canSubmit"
            @click="submit"
          >
            Compare Two Figures
          </el-button>

          <el-button size="large" @click="copyTextFromA">
            Copy text A → B
          </el-button>

          <el-button size="large" @click="resetResult">
            Clear Result
          </el-button>
        </div>
      </el-form>
    </el-card>

    <el-card v-if="result" class="result-card">
      <template #header><div class="header-row"><b>Comparison Result</b><el-button size="small" @click="exportCompareData">Export CSV/JSON</el-button></div></template>

      <el-row :gutter="16">
        <el-col :xs="24" :md="8">
          <el-statistic title="Model Winner" :value="winnerText" />
        </el-col>
        <el-col :xs="24" :md="8">
          <el-statistic title="Score Difference" :value="scoreDiffText" />
        </el-col>
        <el-col :xs="24" :md="8">
          <el-statistic title="Confidence" :value="confidenceText" />
        </el-col>
      </el-row>

      <el-alert
        :title="explanationText"
        type="success"
        :closable="false"
        style="margin-top: 16px"
      />

      <el-row :gutter="16" style="margin-top: 16px">
        <el-col :xs="24" :md="12">
          <el-card shadow="never">
            <template #header><b>Overall Score</b></template>
            <LineChart :option="overallOption" />
          </el-card>
        </el-col>

        <el-col :xs="24" :md="12">
          <el-card shadow="never">
            <template #header><b>Dimension Difference: A - B</b></template>
            <LineChart :option="diffOption" />
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" style="margin-top:16px">
        <template #header><b>Dimension-level Comparison</b></template>

        <el-table :data="dimensionRows" border stripe>
          <el-table-column prop="dimension" label="Dimension" min-width="130" />
          <el-table-column prop="score_a" label="Figure A" min-width="110" />
          <el-table-column prop="score_b" label="Figure B" min-width="110" />
          <el-table-column prop="difference" label="A - B" min-width="110" />
          <el-table-column prop="winner" label="Winner" min-width="110">
            <template #default="scope">
              <el-tag
                :type="scope.row.winner === 'A' ? 'primary' : scope.row.winner === 'B' ? 'warning' : 'info'"
              >
                {{ scope.row.winner }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-card>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import LineChart from '../components/LineChart.vue'
import { downloadCsv, downloadJson } from '../utils/exportData'

const checkpoint = ref('./runs/run1/best.pt')
const loading = ref(false)
const result = ref(null)

const figureA = reactive({
  figure_id: 'Figure A',
  caption_text: '',
  context_text: '',
  abstract_text: '',
  meta_text: '',
  image: null,
})

const figureB = reactive({
  figure_id: 'Figure B',
  caption_text: '',
  context_text: '',
  abstract_text: '',
  meta_text: '',
  image: null,
})

const previewA = ref('')
const previewB = ref('')

const dims = ['clarity', 'relevance', 'informativeness', 'structure']

const setPreview = (file, targetRef) => {
  if (targetRef.value) {
    URL.revokeObjectURL(targetRef.value)
  }

  if (!file) {
    targetRef.value = ''
    return
  }

  targetRef.value = URL.createObjectURL(file)
}

const onFileA = (e) => {
  figureA.image = e.target.files?.[0] || null
  setPreview(figureA.image, previewA)
}

const onFileB = (e) => {
  figureB.image = e.target.files?.[0] || null
  setPreview(figureB.image, previewB)
}

const canSubmit = computed(() =>
  Boolean(checkpoint.value && figureA.image && figureB.image)
)

const appendFigure = (form, prefix, figure) => {
  form.append(`${prefix}_figure_id`, figure.figure_id)
  form.append(`${prefix}_caption_text`, figure.caption_text)
  form.append(`${prefix}_context_text`, figure.context_text)
  form.append(`${prefix}_abstract_text`, figure.abstract_text)
  form.append(`${prefix}_meta_text`, figure.meta_text)
  form.append(`${prefix}_image`, figure.image)
}

const submit = async () => {
  if (!canSubmit.value) {
    ElMessage.warning('Please fill in the checkpoint first and upload two images.')
    return
  }

  loading.value = true

  try {
    const form = new FormData()
    form.append('checkpoint', checkpoint.value)

    appendFigure(form, 'a', figureA)
    appendFigure(form, 'b', figureB)

    const { data } = await axios.post('/api/infer/compare-two-images', form)

    result.value = data
  } catch (err) {
    const detail = err?.response?.data?.detail || 'The comparison between the two images failed.'
    ElMessage.error(String(detail))
  } finally {
    loading.value = false
  }
}

const copyTextFromA = () => {
  figureB.caption_text = figureA.caption_text
  figureB.context_text = figureA.context_text
  figureB.abstract_text = figureA.abstract_text
  figureB.meta_text = figureA.meta_text
}

const resetResult = () => {
  result.value = null
}

const winnerText = computed(() => {
  if (!result.value) return '-'
  if (result.value.winner === 'tie') return 'Tie'
  return result.value.winner === 'A' ? 'Figure A' : 'Figure B'
})

const scoreDiffText = computed(() => {
  if (!result.value) return '-'
  return Number(result.value.score_difference_a_minus_b || 0).toFixed(3)
})

const confidenceText = computed(() => {
  if (!result.value) return '-'
  return result.value.confidence || 'medium'
})

const explanationText = computed(() => {
  if (!result.value) return ''

  if (result.value.winner === 'tie') {
    return 'The model predicts that the two figures have very similar overall quality.'
  }

  const winner = result.value.winner === 'A' ? 'Figure A' : 'Figure B'
  const diff = Math.abs(result.value.score_difference_a_minus_b || 0).toFixed(3)

  return `${winner} is predicted to have higher overall quality. Absolute score difference: ${diff}.`
})

const dimensionRows = computed(() =>
  result.value?.dimension_comparison || []
)


const compareExportRows = computed(() => [
  { chart: 'overall_score', figure: 'A', value: result.value?.figure_a?.overall_score ?? null },
  { chart: 'overall_score', figure: 'B', value: result.value?.figure_b?.overall_score ?? null },
  ...dimensionRows.value.map(row => ({ chart: 'dimension_comparison', ...row })),
])
const exportCompareData = () => {
  downloadCsv('two_image_comparison_visualization_data.csv', compareExportRows.value)
  downloadJson('two_image_comparison_visualization_data.json', {
    result: result.value,
    rows: compareExportRows.value,
  })
}

const overallOption = computed(() => ({
  xAxis: {
    type: 'category',
    data: ['Figure A', 'Figure B'],
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 5,
  },
  series: [
    {
      type: 'bar',
      data: [
        result.value?.figure_a?.overall_score || 0,
        result.value?.figure_b?.overall_score || 0,
      ],
    },
  ],
}))

const diffOption = computed(() => ({
  xAxis: {
    type: 'category',
    data: dims,
  },
  yAxis: {
    type: 'value',
  },
  series: [
    {
      type: 'bar',
      data: dims.map(d => {
        const row = dimensionRows.value.find(x => x.dimension === d)
        return row ? row.difference : 0
      }),
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
.result-card {
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

.image-card {
  margin-bottom: 16px;
  border-radius: 10px;
}

.preview-wrapper {
  margin-top: 10px;
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