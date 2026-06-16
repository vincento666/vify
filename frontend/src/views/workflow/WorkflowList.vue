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

    <a-table :data-source="workflows" :loading="loading" class="workflow-table" row-key="id" :pagination="false" size="middle">
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
          <div class="action-buttons">
            <a-button size="small" @click="viewDetail(row)">查看</a-button>
            <a-button size="small" type="primary" ghost @click="$router.push({ name: 'HifyWorkflowsCanvas', params: { id: row.id } })">画布</a-button>
            <a-popconfirm title="确认删除这个工作流？" ok-text="确认" cancel-text="取消" @confirm="handleDelete(row.id)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </div>
        </template>
      </a-table-column>
    </a-table>

    <!-- 详情抽屉 -->
    <a-drawer v-model:open="drawerVisible" width="37.5rem" placement="right" :closable="false" @close="drawerVisible = false">
      <template #title>
        <div class="drawer-title">
          <span>工作流详情</span>
          <button type="button" class="drawer-close-button" aria-label="关闭工作流详情" @click="drawerVisible = false">
            <CloseOutlined />
          </button>
        </div>
      </template>
      <div v-if="detail" class="detail-panel">
        <div class="detail-meta">
          <a-descriptions :column="2" bordered size="small">
            <a-descriptions-item label="名称">{{ detail.name }}</a-descriptions-item>
            <a-descriptions-item label="状态">
              <a-tag :color="statusColor(detail.status)">
                {{ statusLabel(detail.status) }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="描述" :span="2">{{ detail.description || '-' }}</a-descriptions-item>
          </a-descriptions>
        </div>

        <div class="detail-section">
          <h4>节点 ({{ detail.nodes.length }})</h4>
          <div v-for="node in detail.nodes" :key="node.nodeKey" class="node-card">
            <div class="node-header">
              <a-tag :color="nodeTypeColor(node.type)">{{ node.type }}</a-tag>
              <span class="node-key">{{ node.nodeKey }}</span>
              <span class="node-name">{{ node.name }}</span>
            </div>
            <div v-if="node.config && Object.keys(node.config).length" class="node-config">
              <pre>{{ JSON.stringify(node.config, null, 2) }}</pre>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4>连线 ({{ detail.edges.length }})</h4>
          <div v-for="(edge, i) in detail.edges" :key="i" class="edge-row">
            <span class="edge-source">{{ edge.sourceNodeKey }}</span>
            <RightOutlined />
            <span class="edge-target">{{ edge.targetNodeKey }}</span>
            <a-tag v-if="edge.condition" color="warning">{{ edge.condition }}</a-tag>
            <a-tag v-else color="default">无条件</a-tag>
          </div>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { CloseOutlined, PlusOutlined, RightOutlined, ShareAltOutlined } from '@ant-design/icons-vue'
import { listWorkflows, getWorkflow, deleteWorkflow, type WorkflowListItem, type WorkflowDetail } from '@/api/workflow'
import WorkflowModuleTabs from './WorkflowModuleTabs.vue'

const loading = ref(false)
const workflows = ref<WorkflowListItem[]>([])
const drawerVisible = ref(false)
const detail = ref<WorkflowDetail | null>(null)

const workflowTableColumnWidths = {
  name: '13.75rem',
  description: '16.25rem',
  status: '6.875rem',
  updatedAt: '11.25rem',
  actions: '14.375rem',
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

async function viewDetail(row: WorkflowListItem) {
  const res = await getWorkflow(row.id) as any
  detail.value = res
  drawerVisible.value = true
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

function nodeTypeColor(type: string) {
  const map: Record<string, string> = {
    START: 'success', END: 'error', LLM: 'processing', CONDITION: 'warning',
    KNOWLEDGE: 'default', API_CALL: 'cyan'
  }
  return map[type] || 'default'
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

.wf-name { display: flex; align-items: center; gap: var(--space-2); }
.wf-icon { color: var(--color-primary-600); }
.action-buttons { display: flex; align-items: center; gap: var(--space-2); }

.detail-section { margin-top: var(--space-5); }
.detail-section h4 { margin: 0 0 var(--space-3); font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }

.node-card {
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-sm);
  padding: 0.625rem 0.75rem;
  margin-bottom: var(--space-2);
  background: var(--color-bg-page);
}
.node-header { display: flex; align-items: center; gap: var(--space-2); }
.node-key { font-family: monospace; font-size: var(--text-xs); color: var(--color-text-secondary); }
.node-name { font-size: var(--text-sm); color: var(--color-text-primary); }
.node-config {
  margin-top: var(--space-2);
  padding: var(--space-2);
  background: var(--color-bg-hover);
  border-radius: var(--radius-xs);
  overflow: auto;
  max-height: 7.5rem;
}
.node-config pre { margin: 0; font-size: 0.6875rem; line-height: 1.5; color: var(--color-text-secondary); }

.edge-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0.375rem 0;
  border-bottom: 1px solid var(--color-border-default);
  font-size: var(--text-sm);
}
.edge-source { font-family: monospace; color: var(--color-primary-600); }
.edge-target { font-family: monospace; color: var(--color-success-600); }

.detail-meta { margin-bottom: var(--space-4); }

.drawer-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.drawer-close-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.drawer-close-button:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}
</style>
