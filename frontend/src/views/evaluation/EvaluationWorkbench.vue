<template>
  <div class="evaluation-page">
    <header class="evaluation-header">
      <div>
        <h2>评测</h2>
        <p>用评测集、评估器和实验运行验证 Agent 质量变化</p>
      </div>
    </header>

    <a-tabs v-model:activeKey="activeTab" class="evaluation-tabs">
      <a-tab-pane
        v-for="tab in EVALUATION_TABS"
        :key="tab.key"
        :disabled="tab.disabled"
      >
        <template #tab>
          <span>{{ tab.label }}</span>
        </template>
      </a-tab-pane>
    </a-tabs>

    <section class="tab-summary">
      <div>
        <h3>{{ activeTabMeta.cnLabel }}</h3>
        <p>{{ activeTabMeta.description }}</p>
      </div>
      <a-tag v-if="activeTabMeta.disabled" color="default">MVP 后开放</a-tag>
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
import { useRoute } from 'vue-router'

import { EVALUATION_TABS, getActiveEvaluationTab, type EvaluationTabKey } from './evaluationTabs'
import EvalSetsPanel from './EvalSetsPanel.vue'
import EvaluatorsPanel from './EvaluatorsPanel.vue'
import CompareAnalysisPanel from './CompareAnalysisPanel.vue'
import ExperimentsPanel from './ExperimentsPanel.vue'
import RunRecordsPanel from './RunRecordsPanel.vue'

const route = useRoute()
const activeTab = ref<EvaluationTabKey>(getActiveEvaluationTab(String(route.query.tab || route.meta.defaultEvaluationTab || '')))
const activeTabMeta = computed(() => EVALUATION_TABS.find((tab) => tab.key === activeTab.value) || EVALUATION_TABS[0])
</script>

<style scoped>
.evaluation-page {
  min-height: calc(100vh - 7rem);
}

.evaluation-header {
  margin-bottom: 1.125rem;
}

.evaluation-header h2 {
  margin: 0 0 var(--space-1);
  color: var(--color-text-primary);
  font-size: var(--text-xl);
}

.evaluation-header p,
.tab-summary p,
.empty-panel p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
}

.evaluation-tabs {
  margin-bottom: 0.875rem;
}

.tab-summary {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.875rem;
  padding: 0.875rem 0;
  border-bottom: 0.0625rem solid var(--color-border-default);
}

.tab-summary h3,
.empty-panel h3 {
  margin: 0 0 0.375rem;
  color: var(--color-text-primary);
  font-size: var(--text-md);
}

.empty-panel {
  min-height: 18.75rem;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 0.875rem;
  border-bottom: 0.0625rem solid var(--color-border-default);
}

.disabled-panel {
  opacity: 0.75;
}
</style>
