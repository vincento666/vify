<template>
  <div class="chatflow-list">
    <WorkflowModuleTabs />

    <div class="page-header">
      <div>
        <h2 class="page-title">对话流</h2>
        <p class="page-desc">管理面向对话场景的流程编排</p>
      </div>
      <el-button type="primary" @click="$router.push('/chatflows/create')">
        <el-icon><Plus /></el-icon>新建对话流
      </el-button>
    </div>

    <el-table v-if="chatflows.length" :data="chatflows" v-loading="loading" class="workflow-table" stripe>
      <el-table-column prop="name" label="名称" :min-width="workflowTableColumnWidths.name">
        <template #default="{ row }">
          <div class="wf-name">
            <el-icon class="wf-icon"><ChatLineRound /></el-icon>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" :min-width="workflowTableColumnWidths.description" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" :width="workflowTableColumnWidths.status">
        <template #default="{ row }">
          <el-tag :type="row.status === 'PUBLISHED' ? 'success' : row.status === 'DISABLED' ? 'danger' : 'info'" size="small">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" :width="workflowTableColumnWidths.updatedAt">
        <template #default="{ row }">{{ formatTime(row.updatedAt || row.createdAt) }}</template>
      </el-table-column>
      <el-table-column label="操作" :width="workflowTableColumnWidths.actions" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="$router.push(`/chatflows/${row.id}/canvas`)">查看</el-button>
          <el-button size="small" type="primary" plain @click="$router.push(`/chatflows/${row.id}/canvas`)">画布</el-button>
          <el-popconfirm title="确认删除这个对话流？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button size="small" type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div v-else class="empty-state">
      <el-empty description="对话流画布已就绪，可创建对话流程并完成试运行与发布">
        <el-button type="primary" @click="$router.push('/chatflows/create')">创建对话流</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatLineRound, Plus } from '@element-plus/icons-vue'

import { deleteChatflow, listChatflows, type WorkflowListItem } from '@/api/workflow'
import WorkflowModuleTabs from './WorkflowModuleTabs.vue'

const chatflows = ref<WorkflowListItem[]>([])
const loading = ref(false)

// Element Plus table column props parse CSS unit strings as pixel integers,
// so rem strings collapse columns. Keep these numeric props scoped here.
const workflowTableColumnWidths = {
  name: 220,
  description: 260,
  status: 110,
  updatedAt: 180,
  actions: 230,
}

async function loadChatflows() {
  loading.value = true
  try {
    const page = await listChatflows()
    chatflows.value = page.list
  } finally {
    loading.value = false
  }
}

async function handleDelete(id: number) {
  await deleteChatflow(id)
  ElMessage.success('已删除')
  await loadChatflows()
}

function statusLabel(status: string) {
  return { DRAFT: '草稿', PUBLISHED: '已发布', DISABLED: '已禁用' }[status] || status
}

function formatTime(value: string) {
  if (!value) return '-'
  return value.replace('T', ' ').substring(0, 16)
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
  margin-bottom: var(--space-5);
}

.page-title {
  margin: 0 0 var(--space-1);
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.page-desc {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--el-text-color-secondary);
}

.empty-state {
  min-height: 20rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--radius-md);
  background: var(--el-bg-color);
}

.workflow-table {
  width: 100%;
}

.wf-name {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.wf-icon {
  color: var(--el-color-primary);
}
</style>
