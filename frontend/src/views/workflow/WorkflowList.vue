<template>
  <div class="workflow-list">
    <WorkflowModuleTabs />

    <div class="page-header">
      <div>
        <h2 class="page-title">工作流</h2>
        <p class="page-desc">管理智能客服分类等工作流配置</p>
      </div>
      <a-button type="primary" @click="$router.push({ name: 'HifyWorkflowsCreate' })">
        <template #icon><PlusOutlined /></template>
        新建工作流
      </a-button>
    </div>

    <a-table :data-source="workflows" :loading="loading" class="workflow-table" row-key="id" :pagination="false" size="middle" :custom-row="workflowRow">
      <a-table-column data-index="name" title="名称" :width="workflowTableColumnWidths.name">
        <template #default="{ record: row }">
          <div class="wf-name">
            <ShareAltOutlined class="wf-icon" />
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
            <a-popconfirm title="确认删除这个工作流？" ok-text="确认" cancel-text="取消" @confirm="handleDelete(row.id)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </div>
        </template>
      </a-table-column>
    </a-table>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined, ShareAltOutlined } from '@ant-design/icons-vue'
import { listWorkflows, deleteWorkflow, type WorkflowListItem } from '@/api/workflow'
import WorkflowModuleTabs from './WorkflowModuleTabs.vue'

const router = useRouter()
const loading = ref(false)
const workflows = ref<WorkflowListItem[]>([])

const workflowTableColumnWidths = {
  name: '13.75rem',
  description: '16.25rem',
  status: '6.875rem',
  updatedAt: '11.25rem',
  actions: '5rem',
}

async function fetchList() {
  loading.value = true
  try {
    const res = await listWorkflows() as any
    workflows.value = res?.list || []
  } finally {
    loading.value = false
  }
}

function workflowRow(row: WorkflowListItem) {
  return {
    onClick: () => router.push({ name: 'HifyWorkflowsCanvas', params: { id: row.id } }),
  }
}

async function handleDelete(id: number) {
  await deleteWorkflow(id)
  message.success('已删除')
  fetchList()
}

function statusLabel(s: string) {
  return { DRAFT: '草稿', PUBLISHED: '已发布', DISABLED: '已禁用' }[s] || s
}

function statusColor(s: string) {
  return { DRAFT: 'default', PUBLISHED: 'success', DISABLED: 'error' }[s] || 'default'
}

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 16)
}

onMounted(fetchList)
</script>

<style scoped>
.workflow-list { padding: 0; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-5);
}
.page-title { margin: 0 0 var(--space-1); font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.page-desc { margin: 0; font-size: var(--text-sm); color: var(--color-text-secondary); }

.workflow-table { width: 100%; }
.workflow-table :deep(.ant-table-tbody > tr) { cursor: pointer; }

.wf-name { display: flex; align-items: center; gap: var(--space-2); }
.wf-icon { color: var(--color-primary-600); }
.action-buttons { display: flex; align-items: center; gap: var(--space-2); }
</style>
