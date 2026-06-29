<template>
  <div>
    <el-card>
      <template #header><b>Multiple experimental comparisons</b></template>
      <el-input v-model="runIdsText" type="textarea" :rows="3" placeholder="One run_id per line" />
      <el-button style="margin-top:12px" @click="load">Loading comparison</el-button>
    </el-card>
    <el-card style="margin-top:16px" v-if="rows.length">
      <el-table :data="rows" border>
        <el-table-column prop="run_id" label="run_id" width="140" />
        <el-table-column prop="clarity" label="clarity spearman" />
        <el-table-column prop="relevance" label="relevance spearman" />
        <el-table-column prop="informativeness" label="informativeness spearman" />
        <el-table-column prop="structure" label="structure spearman" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api/client'

const runIdsText = ref('')
const rows = ref([])

const load = async () => {
  const runIds = runIdsText.value.split(/\s+/).filter(Boolean)
  rows.value = []
  for (const runId of runIds) {
    const { data } = await api.get(`/runs/${runId}/summary`)
    rows.value.push({
      run_id: runId,
      clarity: data.summary?.clarity?.spearman ?? '-',
      relevance: data.summary?.relevance?.spearman ?? '-',
      informativeness: data.summary?.informativeness?.spearman ?? '-',
      structure: data.summary?.structure?.spearman ?? '-',
    })
  }
}
</script>
