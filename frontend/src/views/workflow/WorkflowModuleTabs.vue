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
  margin-bottom: 18px;
}

.workflow-module-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.workflow-module-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: var(--el-border-color-lighter);
}

.workflow-module-tabs :deep(.el-tabs__item) {
  height: 36px;
  padding: 0 18px;
  font-size: 13px;
  font-weight: 600;
}
</style>
