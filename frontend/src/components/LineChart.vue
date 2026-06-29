<template>
  <div ref="el" style="width:100%;height:400px"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({ option: { type: Object, required: true } })
const el = ref(null)
let chart = null
let resizeObserver = null

const resize = () => {
  if (chart) chart.resize()
}

const render = () => {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  chart.setOption(props.option, { notMerge: true, lazyUpdate: true })
}

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
  if (window.ResizeObserver && el.value) {
    resizeObserver = new ResizeObserver(() => resize())
    resizeObserver.observe(el.value)
  }
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (resizeObserver) resizeObserver.disconnect()
  if (chart) chart.dispose()
})
</script>
