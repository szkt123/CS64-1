<template>
  <div class="dataset-page">
    <el-card class="page-card">
      <template #header>
        <div class="header-row">
          <div>
            <b>Dataset manual annotation page</b>
          </div>
          <el-button tag="a" href="/batch_1/index.html" target="_blank">Open in a new window</el-button>
        </div>
      </template>
      <iframe class="batch-frame" src="/batch_1/index.html" title="Batch 1 Dataset Annotation"></iframe>
    </el-card>
  </div>
</template>

<script setup>
</script>

<style scoped>
.dataset-page {
  height: calc(100vh - 40px);
}

.page-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.el-card__body) {
  flex: 1;
  padding: 0;
  min-height: 0;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.header-row p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.batch-frame {
  width: 100%;
  height: 100%;
  min-height: 760px;
  border: 0;
  border-radius: 0 0 4px 4px;
  background: #fff;
}
</style>
