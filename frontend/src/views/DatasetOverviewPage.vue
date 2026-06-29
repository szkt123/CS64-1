<template>
  <div class="overview-root">
    <!-- Filter bar -->
    <el-card class="filter-card" style="margin-bottom:16px">
      <template #header>
        <div class="card-header">
          <b>Scientific Figure Quality Dataset</b>
          <el-tag effect="plain">{{ filtered.length.toLocaleString() }} / {{ allData.length.toLocaleString() }} records</el-tag>
        </div>
      </template>
      <el-space wrap>
        <div class="filter-group">
          <span class="filter-label">Venue</span>
          <el-select v-model="selVenues" multiple collapse-tags style="min-width:220px" placeholder="All venues">
            <el-option v-for="v in ALL_VENUES" :key="v" :label="v.replace('_', ' ')" :value="v" />
          </el-select>
        </div>
        <div class="filter-group">
          <span class="filter-label">Source</span>
          <el-select v-model="selSources" multiple collapse-tags style="min-width:160px" placeholder="All sources">
            <el-option label="Human" value="human" />
            <el-option label="GPT-4o" value="gpt" />
          </el-select>
        </div>
        <div class="filter-group">
          <span class="filter-label">Figure Type</span>
          <el-select v-model="selTypes" multiple collapse-tags style="min-width:220px" placeholder="All types">
            <el-option label="Architecture Diagram" value="architecture_diagram" />
            <el-option label="Qualitative Example" value="qualitative_example" />
            <el-option label="Other" value="other" />
          </el-select>
        </div>
        <el-button @click="resetFilters">Reset</el-button>
      </el-space>
    </el-card>

    <!-- Metric cards -->
    <el-row :gutter="12" style="margin-bottom:16px">
      <el-col :span="4" v-for="m in metrics" :key="m.label">
        <el-card class="metric-card" shadow="never">
          <div class="metric-value">{{ m.value }}</div>
          <div class="metric-label">{{ m.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts row 1 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6">
        <el-card shadow="never">
          <template #header><b>Annotation Source</b></template>
          <EChart :option="srcPieOption" style="height:220px" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <template #header><b>Figure Type</b></template>
          <EChart :option="typePieOption" style="height:220px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><b>Records by Venue</b></template>
          <EChart :option="venueBarOption" style="height:220px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts row 2 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><b>Average Score by Dimension</b></template>
          <EChart :option="meanScoreOption" style="height:240px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><b>Most Common Score Combinations</b></template>
          <EChart :option="comboBarOption" style="height:240px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Gallery section -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <b>Representative Images by Score Combination</b>
          <el-tag type="info" effect="plain">Choose any combination to browse examples</el-tag>
        </div>
      </template>

      <el-space wrap style="margin-bottom:12px">
        <div class="filter-group" v-for="dim in DIMS" :key="dim">
          <span class="filter-label">{{ DIM_LABELS[dim] }}</span>
          <el-select v-model="gallery[dim]" style="width:110px">
            <el-option label="Any" value="Any" />
            <el-option v-for="n in [1,2,3,4,5]" :key="n" :label="String(n)" :value="n" />
          </el-select>
        </div>
        <div class="filter-group">
          <span class="filter-label">Sort</span>
          <el-select v-model="gallerySort" style="width:210px">
            <el-option label="Most representative first" value="representative" />
            <el-option label="Highest overall score first" value="high" />
            <el-option label="Lowest overall score first" value="low" />
          </el-select>
        </div>
        <div class="filter-group">
          <span class="filter-label">Show</span>
          <el-select v-model="galleryLimit" style="width:90px">
            <el-option v-for="n in [6,12,18]" :key="n" :label="String(n)" :value="n" />
          </el-select>
        </div>
      </el-space>

      <div class="gallery-summary">{{ gallerySummary }}</div>

      <div v-if="loading" style="text-align:center;padding:40px">
        <el-icon :size="32"><Loading /></el-icon>
        <div style="margin-top:8px;color:#94a3b8">Loading dataset...</div>
      </div>
      <div v-else class="gallery-grid">
        <div v-for="row in galleryRows" :key="row.paper_id + row.figure_id" class="gallery-card">
          <div class="gallery-img-wrap">
            <img
              v-if="row.image_path"
              :src="'/' + row.image_path"
              :alt="row.figure_id"
              class="gallery-img"
              @error="e => {
                const hfUrl = 'https://huggingface.co/datasets/Jhao0930/capstone-figures/resolve/main/' + row.image_path;
                if (e.target.src !== hfUrl) {
                  e.target.src = hfUrl;
                } else {
                  e.target.closest('.gallery-img-wrap').classList.add('no-img');
                }
              }"
            />
            <div class="gallery-img-placeholder">Image not available</div>
          </div>
          <div class="gallery-meta">
            <div class="gallery-combo">{{ comboLabel(row) }}</div>
            <div class="gallery-tags">
              <el-tag size="small" effect="plain" style="margin-right:4px">{{ row.venue.replace('_', ' ') }}</el-tag>
              <el-tag size="small" effect="plain" type="success" style="margin-right:4px">{{ TYPE_LABELS[row.figure_type] || row.figure_type }}</el-tag>
              <el-tag size="small" effect="plain" type="warning">{{ row.source === 'human' ? 'Human' : 'GPT-4o' }}</el-tag>
            </div>
            <div class="gallery-score-badges">
              <span v-for="dim in DIMS" :key="dim" class="score-badge" :style="{ backgroundColor: DIM_COLORS[dim] }">
                {{ DIM_LABELS[dim] }} {{ row[dim] }}
              </span>
            </div>
            <p class="gallery-caption">{{ row.caption || 'No caption available.' }}</p>
            <div class="gallery-ids">
              <span class="id-label">Paper:</span> <code>{{ row.paper_id }}</code>
              <span class="id-label" style="margin-left:8px">Fig:</span> <code>{{ row.figure_id }}</code>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import EChart from '../components/EChart.vue'

// ── Constants ──────────────────────────────────────────────────────────────────
const DIMS = ['clarity', 'relevance', 'informativeness', 'structure']
const DIM_LABELS = { clarity: 'Clarity', relevance: 'Relevance', informativeness: 'Informativeness', structure: 'Structure' }
const DIM_COLORS = { clarity: '#4C72B0', relevance: '#DD8452', informativeness: '#55A868', structure: '#C44E52' }
const ALL_VENUES = ['ICLR_2024', 'ICLR_2025', 'NeurIPS_2023', 'NeurIPS_2024', 'ICML_2023', 'ICML_2024']
const VENUE_COLORS = { ICLR_2024: '#4C72B0', ICLR_2025: '#55A868', NeurIPS_2023: '#C44E52', NeurIPS_2024: '#8172B2', ICML_2023: '#CCB974', ICML_2024: '#64B5CD' }
const SOURCE_COLORS = { human: '#4C72B0', gpt: '#DD8452' }
const TYPE_COLORS = { architecture_diagram: '#4C72B0', qualitative_example: '#55A868', other: '#DD8452' }
const TYPE_LABELS = { architecture_diagram: 'Architecture Diagram', qualitative_example: 'Qualitative Example', other: 'Other' }

// ── State ──────────────────────────────────────────────────────────────────────
const loading = ref(true)
const allData = ref([])
const selVenues = ref([...ALL_VENUES])
const selSources = ref(['human', 'gpt'])
const selTypes = ref(['architecture_diagram', 'qualitative_example', 'other'])
const gallerySort = ref('representative')
const galleryLimit = ref(12)
const gallery = reactive({ clarity: 'Any', relevance: 'Any', informativeness: 'Any', structure: 'Any' })

onMounted(async () => {
  const res = await fetch('/dataset_overview.json')
  allData.value = await res.json()
  loading.value = false
})

function resetFilters() {
  selVenues.value = [...ALL_VENUES]
  selSources.value = ['human', 'gpt']
  selTypes.value = ['architecture_diagram', 'qualitative_example', 'other']
}

// ── Filtered data ──────────────────────────────────────────────────────────────
const filtered = computed(() => {
  const v = selVenues.value.length ? selVenues.value : ALL_VENUES
  const s = selSources.value.length ? selSources.value : ['human', 'gpt']
  const t = selTypes.value.length ? selTypes.value : ['architecture_diagram', 'qualitative_example', 'other']
  return allData.value.filter(r => v.includes(r.venue) && s.includes(r.source) && t.includes(r.figure_type))
})

// ── Metrics ────────────────────────────────────────────────────────────────────
const metrics = computed(() => {
  const f = filtered.value
  if (!f.length) return []
  const avgOverall = f.reduce((sum, r) => sum + DIMS.reduce((s, d) => s + r[d], 0) / DIMS.length, 0) / f.length
  return [
    { label: 'Records', value: f.length.toLocaleString() },
    { label: 'Venues', value: new Set(f.map(r => r.venue)).size },
    { label: 'Human', value: f.filter(r => r.source === 'human').length.toLocaleString() },
    { label: 'GPT-4o', value: f.filter(r => r.source === 'gpt').length.toLocaleString() },
    { label: 'Arch Diagrams', value: f.filter(r => r.figure_type === 'architecture_diagram').length.toLocaleString() },
    { label: 'Avg Score', value: avgOverall.toFixed(2) },
  ]
})

// ── Chart options ──────────────────────────────────────────────────────────────
function countBy(data, key) {
  const map = {}
  for (const r of data) map[r[key]] = (map[r[key]] || 0) + 1
  return map
}

const srcPieOption = computed(() => {
  const c = countBy(filtered.value, 'source')
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', confine: true },
    legend: { orient: 'horizontal', bottom: 0, itemGap: 12, textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie', radius: ['40%', '68%'], center: ['50%', '42%'],
      data: [
        { name: 'Human', value: c['human'] || 0, itemStyle: { color: SOURCE_COLORS.human } },
        { name: 'GPT-4o', value: c['gpt'] || 0, itemStyle: { color: SOURCE_COLORS.gpt } },
      ],
      label: { show: false },
      emphasis: { label: { show: false } },
    }],
  }
})

const typePieOption = computed(() => {
  const c = countBy(filtered.value, 'figure_type')
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', confine: true },
    legend: { orient: 'horizontal', bottom: 0, itemGap: 8, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie', radius: ['40%', '68%'], center: ['50%', '42%'],
      data: Object.entries(TYPE_LABELS).map(([k, name]) => ({
        name, value: c[k] || 0, itemStyle: { color: TYPE_COLORS[k] },
      })),
      label: { show: false },
      emphasis: { label: { show: false } },
    }],
  }
})

const venueBarOption = computed(() => {
  const c = countBy(filtered.value, 'venue')
  const venues = ALL_VENUES.filter(v => c[v])
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: venues.map(v => v.replace('_', '\n')), axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: venues.map(v => ({ value: c[v] || 0, itemStyle: { color: VENUE_COLORS[v] || '#666' } })),
      barMaxWidth: 48,
    }],
    grid: { left: 50, right: 16, top: 12, bottom: 52 },
  }
})

const meanScoreOption = computed(() => {
  const f = filtered.value
  if (!f.length) return {}
  return {
    tooltip: { trigger: 'axis', formatter: p => `${p[0].name}: ${Number(p[0].value).toFixed(3)}` },
    xAxis: { type: 'category', data: DIMS.map(d => DIM_LABELS[d]) },
    yAxis: { type: 'value', min: 1, max: 5 },
    series: [{
      type: 'bar',
      data: DIMS.map(d => ({
        value: +(f.reduce((s, r) => s + r[d], 0) / f.length).toFixed(3),
        itemStyle: { color: DIM_COLORS[d] },
      })),
      barMaxWidth: 60,
      label: { show: true, position: 'top', formatter: p => Number(p.value).toFixed(2) },
    }],
    grid: { left: 50, right: 16, top: 28, bottom: 32 },
  }
})

const comboBarOption = computed(() => {
  const f = filtered.value
  if (!f.length) return {}
  const counts = {}
  for (const r of f) {
    const k = `C${r.clarity}/R${r.relevance}/I${r.informativeness}/S${r.structure}`
    counts[k] = (counts[k] || 0) + 1
  }
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 12)
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: top.map(e => e[0]).reverse(), axisLabel: { fontSize: 11 } },
    series: [{ type: 'bar', data: top.map(e => e[1]).reverse(), barMaxWidth: 24, itemStyle: { color: '#4C72B0' } }],
    grid: { left: 160, right: 40, top: 8, bottom: 28 },
  }
})

// ── Gallery ────────────────────────────────────────────────────────────────────
function comboLabel(row) {
  return `C${row.clarity} / R${row.relevance} / I${row.informativeness} / S${row.structure}`
}

const galleryRows = computed(() => {
  let f = filtered.value.slice()
  for (const dim of DIMS) {
    if (gallery[dim] !== 'Any') f = f.filter(r => r[dim] === gallery[dim])
  }
  if (!f.length) return []

  const comboFreq = {}
  for (const r of f) {
    const k = comboLabel(r); comboFreq[k] = (comboFreq[k] || 0) + 1
  }
  const overall = r => DIMS.reduce((s, d) => s + r[d], 0) / DIMS.length
  const srcRank = r => r.source === 'human' ? 0 : 1

  if (gallerySort.value === 'high') {
    f.sort((a, b) => overall(b) - overall(a) || srcRank(a) - srcRank(b))
  } else if (gallerySort.value === 'low') {
    f.sort((a, b) => overall(a) - overall(b) || srcRank(a) - srcRank(b))
  } else {
    f.sort((a, b) => (comboFreq[comboLabel(b)] - comboFreq[comboLabel(a)]) || srcRank(a) - srcRank(b) || overall(b) - overall(a))
  }
  return f.slice(0, galleryLimit.value)
})

const gallerySummary = computed(() => {
  let f = filtered.value.slice()
  const active = []
  for (const dim of DIMS) {
    if (gallery[dim] !== 'Any') {
      f = f.filter(r => r[dim] === gallery[dim])
      active.push(`${DIM_LABELS[dim]}=${gallery[dim]}`)
    }
  }
  if (!f.length) return 'No figures match this score combination under the current filters.'
  const top = comboLabel(f[0])
  return `${f.length.toLocaleString()} figures match${active.length ? ' (' + active.join(', ') + ')' : ' current filters'}. Showing up to ${galleryLimit.value}. Most common pattern: ${top}.`
})
</script>

<style scoped>
.overview-root {
  min-height: 100%;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-label {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  color: #374151;
}
.metric-card {
  text-align: center;
  padding: 4px 0;
}
.metric-value {
  font-size: 26px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
}
.metric-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}
.gallery-summary {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 14px;
  min-height: 20px;
}
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}
.gallery-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.gallery-img-wrap {
  position: relative;
  height: 200px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.gallery-img {
  width: 100%;
  height: 200px;
  object-fit: contain;
  position: relative;
  z-index: 1;
}
.gallery-img-placeholder {
  position: absolute;
  inset: 0;
  display: none;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-style: italic;
  font-size: 13px;
}
.gallery-img-wrap.no-img .gallery-img { display: none; }
.gallery-img-wrap.no-img .gallery-img-placeholder,
.gallery-img-wrap:not(:has(img)) .gallery-img-placeholder { display: flex; }
.gallery-meta {
  padding: 12px;
}
.gallery-combo {
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 8px;
  color: #1e293b;
}
.gallery-tags {
  margin-bottom: 8px;
}
.gallery-score-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}
.score-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}
.gallery-caption {
  font-size: 12px;
  line-height: 1.5;
  color: #475569;
  margin: 6px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.gallery-ids {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 6px;
}
.id-label {
  font-weight: 600;
  color: #64748b;
}
</style>
