<template>
  <div class="ablation-page">
    <section class="hero">
      <div>
        <p class="eyebrow">Ablation Study</p>
        <h1>Scientific Figure Quality Evaluation</h1>
        <p class="subtitle">
          This dashboard presents the input ablation, denoised full-input comparison,
          and pairwise ranking loss analysis.
        </p>
      </div>

      <button class="refresh-btn" @click="loadCsv">
        Refresh Results
      </button>
    </section>

    <div v-if="loading" class="message-card">
      Loading ablation results...
    </div>

    <div v-else-if="error" class="error-card">
      {{ error }}
    </div>

    <template v-else>
      <section class="cards">
        <div class="card">
          <p class="card-label">Total Settings</p>
          <h2>{{ rows.length }}</h2>
          <p class="card-note">Ablation experiments</p>
        </div>

        <div class="card">
          <p class="card-label">Best Macro MAE ↓</p>
          <h2>{{ formatNumber(bestMae?.macro_mae) }}</h2>
          <p class="card-note">{{ displaySetting(bestMae?.setting) }}</p>
        </div>

        <div class="card">
          <p class="card-label">Best Macro MSE ↓</p>
          <h2>{{ formatNumber(bestMse?.macro_mse) }}</h2>
          <p class="card-note">{{ displaySetting(bestMse?.setting) }}</p>
        </div>

        <div class="card">
          <p class="card-label">Best Macro Spearman ↑</p>
          <h2>{{ formatNumber(bestSpearman?.macro_spearman) }}</h2>
          <p class="card-note">{{ displaySetting(bestSpearman?.setting) }}</p>
        </div>

        <div class="card">
          <p class="card-label">Denoising Gain</p>
          <h2>+{{ formatNumber(denoiseSpearmanGain) }}</h2>
          <p class="card-note">Spearman: full_raw → full</p>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>Macro Metrics Comparison</h2>
            <p>Lower Macro MAE and Macro MSE are better. Higher Macro Spearman is better.</p>
          </div>
        </div>

        <div class="chart-list">
          <div
            v-for="row in orderedRows"
            :key="row.setting"
            class="chart-row"
          >
            <div class="setting-block">
              <div class="setting-title">{{ displaySetting(row.setting) }}</div>
              <div class="setting-subtitle">{{ settingDescription(row.setting) }}</div>
            </div>

            <div class="bars">
              <div class="metric-line">
                <span class="metric-name">MAE</span>
                <div class="bar-bg">
                  <div
                    class="bar mae-bar"
                    :style="{ width: maeWidth(row.macro_mae) + '%' }"
                  ></div>
                </div>
                <span class="metric-value">{{ formatNumber(row.macro_mae) }}</span>
              </div>

              <div class="metric-line">
                <span class="metric-name">MSE</span>
                <div class="bar-bg">
                  <div
                    class="bar mse-bar"
                    :style="{ width: mseWidth(row.macro_mse) + '%' }"
                  ></div>
                </div>
                <span class="metric-value">{{ formatNumber(row.macro_mse) }}</span>
              </div>

              <div class="metric-line">
                <span class="metric-name">Spearman</span>
                <div class="bar-bg">
                  <div
                    class="bar spearman-bar"
                    :style="{ width: spearmanWidth(row.macro_spearman) + '%' }"
                  ></div>
                </div>
                <span class="metric-value">{{ formatNumber(row.macro_spearman) }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>Detailed Results</h2>
            <p>Full evaluation metrics for each ablation setting.</p>
          </div>
        </div>

        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Setting</th>
                <th>Macro MAE ↓</th>
                <th>Macro MSE ↓</th>
                <th>Macro Spearman ↑</th>
                <th>Clarity MAE</th>
                <th>Relevance MAE</th>
                <th>Info MAE</th>
                <th>Structure MAE</th>
                <th>Ranking Loss</th>
                <th>Weight</th>
                <th>Batch</th>
                <th>Max Text</th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="row in orderedRows" :key="row.setting">
                <td class="strong">{{ displaySetting(row.setting) }}</td>
                <td>{{ formatNumber(row.macro_mae) }}</td>
                <td>{{ formatNumber(row.macro_mse) }}</td>
                <td>{{ formatNumber(row.macro_spearman) }}</td>
                <td>{{ formatNumber(row.clarity_mae) }}</td>
                <td>{{ formatNumber(row.relevance_mae) }}</td>
                <td>{{ formatNumber(row.informativeness_mae) }}</td>
                <td>{{ formatNumber(row.structure_mae) }}</td>
                <td>
                  <span
                    class="tag"
                    :class="isRankingOn(row) ? 'tag-on' : 'tag-off'"
                  >
                    {{ isRankingOn(row) ? 'On' : 'Off' }}
                  </span>
                </td>
                <td>{{ row.ranking_weight || 0 }}</td>
                <td>{{ row.batch_size }}</td>
                <td>{{ row.max_text_length }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel interpretation">
        <h2>Interpretation</h2>

        <div class="insight-grid">
          <div class="insight-card">
            <h3>Input Ablation</h3>
            <p>
              The image_caption setting achieves the lowest Macro MAE and Macro MSE,
              suggesting that adding figure captions provides the most stable support
              for absolute score regression. Meanwhile, the image_caption_context setting
              improves Macro Spearman compared with image_caption, indicating that citing
              context is more useful for ranking-oriented quality assessment.
            </p>
          </div>

          <div class="insight-card">
            <h3>Denoised Full Input</h3>
            <p>
              The denoised full setting improves over full_raw. Macro MAE changes from
              {{ formatNumber(fullRaw?.macro_mae) }} to {{ formatNumber(full?.macro_mae) }},
              Macro MSE changes from {{ formatNumber(fullRaw?.macro_mse) }} to
              {{ formatNumber(full?.macro_mse) }}, and Macro Spearman changes from
              {{ formatNumber(fullRaw?.macro_spearman) }} to {{ formatNumber(full?.macro_spearman) }}.
              This suggests that filtering noisy textual fields can improve both error-based
              prediction accuracy and rank correlation.
            </p>
          </div>

          <div class="insight-card">
            <h3>Ranking Loss</h3>
            <p>
              The full_rank_w010 setting achieves the highest Macro Spearman of
              {{ formatNumber(bestSpearman?.macro_spearman) }}. Although ranking loss does
              not produce the lowest Macro MAE or Macro MSE, it improves the model's ability
              to preserve relative quality ordering, which is important for comparing figure
              quality across samples.
            </p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

const CSV_PATH = '/results/ablation_summary.csv'

const rows = ref([])
const loading = ref(false)
const error = ref('')

const order = [
  'image_only',
  'image_caption',
  'image_caption_context',
  'full_raw',
  'full',
  'full_rank_w005',
  'full_rank_w010',
]

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/)

  if (lines.length < 2) {
    return []
  }

  const headers = splitCsvLine(lines[0])

  return lines.slice(1).map(line => {
    const values = splitCsvLine(line)
    const row = {}

    headers.forEach((header, index) => {
      const raw = values[index] ?? ''
      row[header] = convertValue(raw)
    })

    return row
  })
}

function splitCsvLine(line) {
  const result = []
  let current = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i++) {
    const char = line[i]

    if (char === '"') {
      inQuotes = !inQuotes
    } else if (char === ',' && !inQuotes) {
      result.push(current)
      current = ''
    } else {
      current += char
    }
  }

  result.push(current)
  return result.map(v => v.trim())
}

function convertValue(value) {
  if (value === '') {
    return ''
  }

  if (value === 'TRUE') {
    return true
  }

  if (value === 'FALSE') {
    return false
  }

  const num = Number(value)

  if (!Number.isNaN(num) && value !== '') {
    return num
  }

  return value
}

async function loadCsv() {
  loading.value = true
  error.value = ''

  try {
    const response = await fetch(CSV_PATH)

    if (!response.ok) {
      throw new Error(`Cannot load ${CSV_PATH}`)
    }

    const text = await response.text()
    rows.value = parseCsv(text)
  } catch (err) {
    error.value = err.message || String(err)
  } finally {
    loading.value = false
  }
}

const orderedRows = computed(() => {
  return [...rows.value].sort((a, b) => {
    return order.indexOf(a.setting) - order.indexOf(b.setting)
  })
})

const bestMae = computed(() => {
  const valid = rows.value.filter(r => Number.isFinite(Number(r.macro_mae)))

  if (!valid.length) {
    return null
  }

  return valid.reduce((best, row) => {
    return Number(row.macro_mae) < Number(best.macro_mae) ? row : best
  })
})

const bestMse = computed(() => {
  const valid = rows.value.filter(r => Number.isFinite(Number(r.macro_mse)))

  if (!valid.length) {
    return null
  }

  return valid.reduce((best, row) => {
    return Number(row.macro_mse) < Number(best.macro_mse) ? row : best
  })
})

const bestSpearman = computed(() => {
  const valid = rows.value.filter(r => Number.isFinite(Number(r.macro_spearman)))

  if (!valid.length) {
    return null
  }

  return valid.reduce((best, row) => {
    return Number(row.macro_spearman) > Number(best.macro_spearman) ? row : best
  })
})

const maxMae = computed(() => {
  const values = rows.value
    .map(r => Number(r.macro_mae))
    .filter(Number.isFinite)

  return values.length ? Math.max(...values) : 1
})
const maxMse = computed(() => {
  const values = rows.value
    .map(r => Number(r.macro_mse))
    .filter(Number.isFinite)

  return values.length ? Math.max(...values) : 1
})

const fullRaw = computed(() => {
  return rows.value.find(r => r.setting === 'full_raw')
})

const full = computed(() => {
  return rows.value.find(r => r.setting === 'full')
})

const denoiseSpearmanGain = computed(() => {
  if (!fullRaw.value || !full.value) {
    return null
  }

  return Number(full.value.macro_spearman) - Number(fullRaw.value.macro_spearman)
})

function displaySetting(setting) {
  const names = {
    image_only: 'Image Only',
    image_caption: 'Image + Caption',
    image_caption_context: 'Image + Caption + Context',
    full_raw: 'Full Raw',
    full: 'Full Denoised',
    full_rank_w005: 'Full Denoised + Rank 0.05',
    full_rank_w010: 'Full Denoised + Rank 0.10',
  }

  return names[setting] || setting || '-'
}

function settingDescription(setting) {
  const descriptions = {
    image_only: 'Visual baseline',
    image_caption: 'Adds figure caption',
    image_caption_context: 'Adds citing paragraphs',
    full_raw: 'Original full input with noisy fields',
    full: 'Denoised full input',
    full_rank_w005: 'Denoised full + pairwise ranking loss',
    full_rank_w010: 'Best ranking configuration',
  }

  return descriptions[setting] || ''
}

function formatNumber(value) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  const num = Number(value)

  if (!Number.isFinite(num)) {
    return '-'
  }

  return num.toFixed(4)
}

function maeWidth(value) {
  const num = Number(value)

  if (!Number.isFinite(num) || maxMae.value <= 0) {
    return 0
  }

  return Math.max(4, (num / maxMae.value) * 100)
}

function mseWidth(value) {
  const num = Number(value)

  if (!Number.isFinite(num) || maxMse.value <= 0) {
    return 0
  }

  return Math.max(4, (num / maxMse.value) * 100)
}

function spearmanWidth(value) {
  const num = Number(value)

  if (!Number.isFinite(num)) {
    return 0
  }

  return Math.max(4, Math.min(100, num * 100))
}

function isRankingOn(row) {
  return row.use_ranking_loss === true || String(row.use_ranking_loss).toLowerCase() === 'true'
}

onMounted(() => {
  loadCsv()
})
</script>

<style scoped>
.ablation-page {
  padding: 28px;
  color: #172033;
  background: #f8fafc;
  min-height: 100vh;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  padding: 28px;
  margin-bottom: 22px;
  border-radius: 24px;
  background: linear-gradient(135deg, #eef4ff, #ffffff);
  border: 1px solid #e2e8f0;
}

.eyebrow {
  margin: 0 0 8px;
  color: #2563eb;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 13px;
}

h1 {
  margin: 0;
  font-size: 34px;
  line-height: 1.15;
}

.subtitle {
  margin: 12px 0 0;
  color: #64748b;
  max-width: 760px;
  line-height: 1.6;
}

.refresh-btn {
  height: 42px;
  padding: 0 18px;
  border: none;
  border-radius: 14px;
  background: #2563eb;
  color: white;
  font-weight: 700;
  cursor: pointer;
}

.cards {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.card,
.panel,
.message-card,
.error-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 22px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}

.card {
  padding: 22px;
}

.card-label {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.card h2 {
  margin: 10px 0 6px;
  font-size: 30px;
}

.card-note {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.panel {
  padding: 24px;
  margin-bottom: 20px;
}

.panel-header {
  margin-bottom: 18px;
}

.panel-header h2,
.interpretation h2 {
  margin: 0 0 6px;
}

.panel-header p {
  margin: 0;
  color: #64748b;
}

.chart-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.chart-row {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 18px;
  align-items: center;
  padding: 14px;
  border-radius: 18px;
  background: #f8fafc;
}

.setting-title {
  font-weight: 800;
}

.setting-subtitle {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
}

.bars {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.metric-line {
  display: grid;
  grid-template-columns: 90px 1fr 80px;
  gap: 10px;
  align-items: center;
}

.metric-name {
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.bar-bg {
  height: 12px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.bar {
  height: 100%;
  border-radius: 999px;
}

.mae-bar {
  background: #f97316;
}

.mse-bar {
  background: #10b981;
}

.spearman-bar {
  background: #2563eb;
}

.metric-value {
  font-variant-numeric: tabular-nums;
  color: #334155;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

th {
  text-align: left;
  background: #f1f5f9;
  color: #475569;
  font-weight: 800;
}

th,
td {
  padding: 13px 12px;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

.strong {
  font-weight: 800;
}

.tag {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 12px;
}

.tag-on {
  color: #166534;
  background: #dcfce7;
}

.tag-off {
  color: #475569;
  background: #f1f5f9;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.insight-card {
  padding: 18px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
}

.insight-card h3 {
  margin: 0 0 8px;
}

.insight-card p {
  margin: 0;
  line-height: 1.65;
  color: #475569;
}

.message-card,
.error-card {
  padding: 24px;
}

.error-card {
  color: #b91c1c;
  background: #fef2f2;
  border-color: #fecaca;
}

@media (max-width: 1100px) {
  .cards,
  .insight-grid {
    grid-template-columns: 1fr 1fr;
  }

  .chart-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .hero {
    flex-direction: column;
  }

  .cards,
  .insight-grid {
    grid-template-columns: 1fr;
  }
}
</style>