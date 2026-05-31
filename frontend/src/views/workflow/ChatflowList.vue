<template>
  <div class="chatflow-list">
    <WorkflowModuleTabs />

    <div class="page-header">
      <div>
        <h2 class="page-title">Chatflow</h2>
        <p class="page-desc">管理面向对话场景的流程编排</p>
      </div>
      <el-button type="primary" @click="$router.push('/chatflows/create')">
        <el-icon><Plus /></el-icon>新建 Chatflow
      </el-button>
    </div>

    <el-table v-if="chatflows.length" :data="chatflows" border>
      <el-table-column prop="name" label="名称" min-width="180" />
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column prop="updatedAt" label="更新时间" width="220" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/chatflows/${row.id}/canvas`)">画布</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-else class="empty-state">
      <el-empty description="Chatflow 资源入口已就绪，图形化画布将在后续 slice 接入">
        <el-button type="primary" @click="$router.push('/chatflows/create')">创建 Chatflow</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'

import { listChatflows, type WorkflowListItem } from '@/api/workflow'
import WorkflowModuleTabs from './WorkflowModuleTabs.vue'

const chatflows = ref<WorkflowListItem[]>([])

async function loadChatflows() {
  const page = await listChatflows()
  chatflows.value = page.list
}

onMounted(loadChatflows)
</script>

<style scoped>
.chatflow-list {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.empty-state {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
}
</style>
