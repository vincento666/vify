<template>
  <div class="workflow-module-tabs">
    <el-tabs :model-value="activePath" @tab-change="handleTabChange">
      <el-tab-pane
        v-for="tab in WORKFLOW_MODULE_TABS"
        :key="tab.flowType"
        :label="tab.label"
        :name="tab.path"
      />
    </el-tabs>
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
    router.push(nextPath)
  }
}
</script>

<style scoped>
.workflow-module-tabs {
  margin-bottom: 1.125rem;
}

.workflow-module-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.workflow-module-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 0.0625rem;
  background: var(--el-border-color-lighter);
}

.workflow-module-tabs :deep(.el-tabs__item) {
  height: 2.25rem;
  padding: 0 1.125rem;
  font-size: 0.8125rem;
  font-weight: 600;
}
</style>
