<template>
  <el-container class="app-shell">
    <el-aside :width="isCollapsed ? '76px' : '264px'" class="app-sidebar">
      <div class="sidebar-inner" :class="{ collapsed: isCollapsed }">
        <div class="brand-row">
          <div class="brand-mark">S</div>
          <div v-show="!isCollapsed" class="brand-text">
            <div class="brand-title">Scientific Image</div>
            <div class="brand-subtitle">Scoring System</div>
          </div>
        </div>

        <button class="collapse-btn" type="button" @click="isCollapsed = !isCollapsed">
          <span>{{ isCollapsed ? '›' : '‹' }}</span>
          <span v-show="!isCollapsed" class="collapse-text">Collapse menu</span>
        </button>

        <el-menu
          router
          :collapse="isCollapsed"
          :default-openeds="isCollapsed ? [] : ['dataset', 'model']"
          :default-active="route.path"
          class="side-menu"
          background-color="transparent"
          text-color="#cbd5e1"
          active-text-color="#ffffff"
          unique-opened
        >
          <el-sub-menu index="dataset">
            <template #title>
              <span>Dataset</span>
            </template>
            <el-menu-item index="/dataset/batch1">Manual Annotation</el-menu-item>
            <el-menu-item index="/dataset/overview">Dataset Overview</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="baseline">
            <template #title>
              <span>Baseline</span>
            </template>
            <el-menu-item index="/baseline">Dashboard</el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="model">
            <template #title>
              <span>Model</span>
            </template>
            <el-menu-item index="/train">Training Config</el-menu-item>
            <el-menu-item index="/monitor">Monitoring</el-menu-item>
            <el-menu-item index="/test-predict">Test Prediction</el-menu-item>
            <el-menu-item index="/results">Results Analysis</el-menu-item>
            <el-menu-item index="/compare">Experiment Compare</el-menu-item>
            <el-menu-item index="/score-image">Single Image Scoring</el-menu-item>
            <el-menu-item index="/compare-two-images">Compare Two Images</el-menu-item>
            <el-menu-item index="/ablation">Ablation Experiment</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </div>
    </el-aside>

    <el-main :class="['app-main', { 'app-main--no-pad': route.path === '/baseline' }]">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isCollapsed = ref(false)
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: #f8fafc;
}

.app-sidebar {
  overflow: hidden;
  background: linear-gradient(180deg, #0f172a 0%, #111827 58%, #020617 100%);
  border-right: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 8px 0 28px rgba(15, 23, 42, 0.12);
  transition: width 0.22s ease;
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 18px 12px;
  box-sizing: border-box;
  overflow-x: hidden;
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 50px;
  padding: 4px 8px 16px;
}

.brand-mark {
  display: grid;
  flex: 0 0 38px;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 12px;
  color: #fff;
  font-size: 19px;
  font-weight: 800;
  background: linear-gradient(135deg, #2563eb, #38bdf8);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.35);
}

.brand-text {
  min-width: 0;
  color: #fff;
  line-height: 1.15;
}

.brand-title,
.brand-subtitle {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.2px;
}

.brand-subtitle {
  font-size: 18px;
  color: #e2e8f0;
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  min-height: 36px;
  margin: 0 0 12px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 12px;
  color: #cbd5e1;
  background: rgba(15, 23, 42, 0.72);
  cursor: pointer;
  transition: all 0.18s ease;
}

.collapse-btn:hover {
  color: #fff;
  border-color: rgba(96, 165, 250, 0.65);
  background: rgba(37, 99, 235, 0.18);
}

.collapse-btn span:first-child {
  font-size: 24px;
  line-height: 1;
}

.collapse-text {
  font-size: 12px;
  letter-spacing: 0.2px;
}

.side-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
}

.side-menu:not(.el-menu--collapse) {
  width: 100%;
}

.menu-icon {
  display: inline-grid;
  width: 28px;
  height: 28px;
  margin-right: 10px;
  place-items: center;
  border-radius: 9px;
  color: #bfdbfe;
  font-size: 13px;
  font-weight: 700;
  background: rgba(59, 130, 246, 0.14);
}

:deep(.el-menu) {
  border-right: 0;
}

:deep(.el-sub-menu__title),
:deep(.el-menu-item) {
  height: 46px;
  margin: 4px 0;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

:deep(.el-sub-menu__title:hover),
:deep(.el-menu-item:hover) {
  color: #fff !important;
  background: rgba(59, 130, 246, 0.18) !important;
}

:deep(.el-menu-item.is-active) {
  color: #fff !important;
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.95), rgba(14, 165, 233, 0.75)) !important;
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.22);
}

:deep(.el-sub-menu .el-menu-item) {
  min-width: 0;
  height: 42px;
  margin-left: 8px;
  padding-left: 50px !important;
  font-size: 13px;
  color: #cbd5e1;
}

:deep(.el-sub-menu__icon-arrow) {
  right: 14px;
}

.collapsed .brand-row {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.collapsed :deep(.el-sub-menu__title),
.collapsed :deep(.el-menu-item) {
  justify-content: center;
  padding: 0 !important;
}

.collapsed .menu-icon {
  margin-right: 0;
}

.app-main {
  min-width: 0;
  padding: 20px;
  background: #f8fafc;
  overflow-x: auto;
}
</style>
