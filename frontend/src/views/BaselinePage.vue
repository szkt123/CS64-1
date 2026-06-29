<template>
  <div class="baseline-wrapper">
    <iframe src="/baseline_dashboard.html" class="baseline-frame" frameborder="0" />
  </div>
</template>

<script setup></script>

<style scoped>
.baseline-wrapper { width:100%; height:100vh; display:flex; flex-direction:column; }
.baseline-frame { flex:1; width:100%; height:100%; border:none; display:block; background:#080a0f; }
</style>