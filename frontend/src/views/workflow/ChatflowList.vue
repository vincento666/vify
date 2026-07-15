<template>
  <div class="chatflow-list">
    <WorkflowModuleTabs />

    <div class="page-header">
      <div>
        <h2 class="page-title">对话流</h2>
        <p class="page-desc">管理面向对话场景的流程编排</p>
      </div>
      <a-button type="primary" @click="$router.push({ name: 'HifyChatflowsCreate' })">
        <template #icon><PlusOutlined /></template>
        新建对话流
      </a-button>
    </div>

    <a-table v-if="chatflows.length" :data-source="chatflows" :loading="loading" class="workflow-table" row-key="id" :pagination="false" size="middle" :custom-row="chatflowRow">
      <a-table-column data-index="name" title="名称" :width="workflowTableColumnWidths.name">
        <template #default="{ record: row }">
          <div class="wf-name">
            <MessageOutlined class="wf-icon" />
            <span>{{ row.name }}</span>
          </div>
        </template>
      </a-table-column>
      <a-table-column data-index="description" title="描述" :width="workflowTableColumnWidths.description" ellipsis />
      <a-table-column data-index="status" title="状态" :width="workflowTableColumnWidths.status">
        <template #default="{ record: row }">
          <a-tag :color="statusColor(row.status)">
            {{ statusLabel(row.status) }}
          </a-tag>
        </template>
      </a-table-column>
      <a-table-column title="更新时间" :width="workflowTableColumnWidths.updatedAt">
        <template #default="{ record: row }">{{ formatTime(row.updatedAt || row.createdAt) }}</template>
      </a-table-column>
      <a-table-column title="操作" :width="workflowTableColumnWidths.actions" fixed="right">
        <template #default="{ record: row }">
          <div class="action-buttons" @click.stop>
            <a-popconfirm title="确认删除这个对话流？" ok-text="确认" cancel-text="取消" @confirm="handleDelete(row.id)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </div>
        </template>
      </a-table-column>
    </a-table>

    <div v-else class="empty-state">
      <a-empty description="对话流画布已就绪，可创建对话流程并完成试运行与发布">
        <a-button type="primary" @click="$router.push({ name: 'HifyChatflowsCreate' })">创建对话流</a-button>
      </a-empty>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { MessageOutlined, PlusOutlined } from '@ant-design/icons-vue'

import { deleteChatflow, listChatflows, type WorkflowListItem } from '@/api/workflow'
import WorkflowModuleTabs from './WorkflowModuleTabs.vue'

const router = useRouter()
const chatflows = ref<WorkflowListItem[]>([])
const loading = ref(false)

const workflowTableColumnWidths = {
  name: '13.75rem',
  description: '16.25rem',
  status: '6.875rem',
  updatedAt: '11.25rem',
  actions: '5rem',
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
  message.success('已删除')
  await loadChatflows()
}

function chatflowRow(row: WorkflowListItem) {
  return {
    onClick: () => router.push({ name: 'HifyChatflowsCanvas', params: { id: row.id } }),
  }
}

function statusLabel(status: string) {
  return { DRAFT: '草稿', PUBLISHED: '已发布', DISABLED: '已禁用' }[status] || status
}

function statusColor(status: string) {
  return { DRAFT: 'default', PUBLISHED: 'success', DISABLED: 'error' }[status] || 'default'
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
  color: var(--color-text-primary);
}

.page-desc {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.empty-state {
  min-height: 20rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
}

.workflow-table {
  width: 100%;
}

.workflow-table :deep(.ant-table-tbody > tr) {
  cursor: pointer;
}

.wf-name {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.wf-icon {
  color: var(--color-primary-600);
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
