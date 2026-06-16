<template>
  <div class="workflow-module-tabs">
    <a-tabs :active-key="activePath" @change="handleTabChange">
      <a-tab-pane
        v-for="tab in WORKFLOW_MODULE_TABS"
        :key="tab.path"
        :tab="tab.label"
      />
    </a-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getActiveWorkflowModulePath, WORKFLOW_MODULE_TABS } from './workflowModuleTabs'

const route = useRoute()
const router = useRouter()
const activePath = computed(() => getActiveWorkflowModulePath(route.path))

function handleTabChange(path: string | number) {
  const nextPath = String(path)
  if (nextPath !== activePath.value) {
    const tab = WORKFLOW_MODULE_TABS.find((item) => item.path === nextPath)
    router.push(tab ? { name: tab.name } : nextPath)
  }
}
</script>

<style scoped>
.workflow-module-tabs {
  margin-bottom: 1.125rem;
}

.workflow-module-tabs :deep(.ant-tabs-nav) {
  margin: 0;
}

.workflow-module-tabs :deep(.ant-tabs-nav::before) {
  height: 0.0625rem;
  border-bottom-color: var(--color-border-default);
}

.workflow-module-tabs :deep(.ant-tabs-tab) {
  height: 2.25rem;
  padding: 0 1.125rem 0.75rem;
  font-size: 0.8125rem;
  font-weight: 600;
}
</style>
