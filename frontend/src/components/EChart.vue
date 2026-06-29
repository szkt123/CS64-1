<template>
  <div ref="el" style="width:100%;height:100%"></div>
</template>

<script setup>
import * as echarts from 'echarts'
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({ option: { type: Object, required: true } })
const el = ref(null)
let chart = null
let ro = null

const resize = () => chart?.resize()

const render = () => {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)
  chart.setOption(props.option, { notMerge: true })
}

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
  if (window.ResizeObserver && el.value) {
    ro = new ResizeObserver(resize)
    ro.observe(el.value)
  }
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  ro?.disconnect()
  chart?.dispose()
})
</script>
