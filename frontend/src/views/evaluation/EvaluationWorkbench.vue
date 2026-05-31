<template>
  <div class="evaluation-page">
    <header class="evaluation-header">
      <div>
        <h2>评测</h2>
        <p>用评测集、评估器和实验运行验证 Agent 质量变化</p>
      </div>
      <el-button type="primary">新建实验</el-button>
    </header>

    <el-tabs v-model="activeTab" class="evaluation-tabs">
      <el-tab-pane
        v-for="tab in EVALUATION_TABS"
        :key="tab.key"
        :name="tab.key"
        :disabled="tab.disabled"
      >
        <template #label>
          <span>{{ tab.label }}</span>
        </template>
      </el-tab-pane>
    </el-tabs>

    <section class="tab-summary">
      <div>
        <h3>{{ activeTabMeta.cnLabel }}</h3>
        <p>{{ activeTabMeta.description }}</p>
      </div>
      <el-tag v-if="activeTabMeta.disabled" type="info" effect="plain">MVP 后开放</el-tag>
    </section>

    <ExperimentsPanel v-if="activeTab === 'experiments'" />

    <EvalSetsPanel v-else-if="activeTab === 'eval-sets'" />

    <EvaluatorsPanel v-else-if="activeTab === 'evaluators'" />

    <RunRecordsPanel v-else-if="activeTab === 'runs'" />

    <CompareAnalysisPanel v-else />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { EVALUATION_TABS, getActiveEvaluationTab, type EvaluationTabKey } from './evaluationTabs'
import EvalSetsPanel from './EvalSetsPanel.vue'
import EvaluatorsPanel from './EvaluatorsPanel.vue'
import CompareAnalysisPanel from './CompareAnalysisPanel.vue'
import ExperimentsPanel from './ExperimentsPanel.vue'
import RunRecordsPanel from './RunRecordsPanel.vue'

const activeTab = ref<EvaluationTabKey>(getActiveEvaluationTab(undefined))
const activeTabMeta = computed(() => EVALUATION_TABS.find((tab) => tab.key === activeTab.value) || EVALUATION_TABS[0])
</script>

<style scoped>
.evaluation-page {
  min-height: calc(100vh - 112px);
}

.evaluation-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
}

.evaluation-header h2 {
  margin: 0 0 4px;
  color: var(--el-text-color-primary);
  font-size: 20px;
}

.evaluation-header p,
.tab-summary p,
.empty-panel p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.evaluation-tabs {
  margin-bottom: 14px;
}

.tab-summary {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.tab-summary h3,
.empty-panel h3 {
  margin: 0 0 6px;
  color: var(--el-text-color-primary);
  font-size: 16px;
}

.empty-panel {
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.disabled-panel {
  opacity: 0.75;
}
</style>
