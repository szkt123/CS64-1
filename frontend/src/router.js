import { createRouter, createWebHistory } from 'vue-router'
import TrainPage from './views/TrainPage.vue'
import MonitorPage from './views/MonitorPage.vue'
import ResultsPage from './views/ResultsPage.vue'
import ComparePage from './views/ComparePage.vue'
import ScoreImagePage from './views/ScoreImagePage.vue'
import CompareTwoImagesPage from './views/CompareTwoImagesPage.vue'
import TestPredictPage from './views/TestPredictPage.vue'
import AblationPage from './views/AblationPage.vue'
import DatasetBatchPage from './views/DatasetBatchPage.vue'
import DatasetOverviewPage from './views/DatasetOverviewPage.vue'
import BaselinePage from './views/BaselinePage.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/train' },
    { path: '/dataset/batch1', component: DatasetBatchPage },
    { path: '/dataset/overview', component: DatasetOverviewPage },
    { path: '/train', component: TrainPage },
    { path: '/monitor/:runId?', component: MonitorPage },
    { path: '/results/:runId?', component: ResultsPage },
    { path: '/compare', component: ComparePage },
    { path: '/score-image', component: ScoreImagePage },
    { path: '/compare-two-images', component: CompareTwoImagesPage },
    { path: '/test-predict/:runId?', component: TestPredictPage },
    { path: '/baseline', component: BaselinePage },
    { path: '/ablation', name: 'Ablation', component: AblationPage },
  ],
})
