<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-left">
        <div class="page-title">Agent 管理</div>
        <div class="page-desc">创建和配置 AI Agent，绑定模型、工具与 System Prompt</div>
      </div>
      <div class="page-header-actions">
        <button class="btn-primary" @click="openCreate">
          <span class="button-icon"><PlusOutlined /></span>
          新增 Agent
        </button>
      </div>
    </div>

    <div class="hify-card agent-card">
      <HifyTable
        ref="tableRef"
        :columns="columns"
        :api="fetchAgents"
        :row-style="agentTableRowStyle"
      >
        <template #name="{ row }">
          <span class="agent-name-cell" :title="row.name">{{ row.name }}</span>
        </template>
        <template #modelName="{ row }">
          <span class="agent-model-cell" :title="modelNameMap[row.modelConfigId] ?? '—'">
            {{ modelNameMap[row.modelConfigId] ?? '—' }}
          </span>
        </template>
        <template #temperature="{ row }">
          <span class="mono">{{ row.temperature.toFixed(1) }}</span>
        </template>
        <template #enabled="{ row }">
          <a-tag :color="row.enabled === 1 ? 'success' : 'default'" class="hify-tag">
            {{ row.enabled === 1 ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <template #createdAt="{ row }">
          <span class="agent-time-cell" :title="formatAgentCreatedAt(row.createdAt)">
            {{ formatAgentCreatedAt(row.createdAt) }}
          </span>
        </template>
        <template #bindings="{ row }">
          <div class="binding-tags">
            <a-tag v-if="row.knowledgeBaseId" color="success" class="hify-tag">知识库</a-tag>
            <a-tag v-if="row.workflowId" color="warning" class="hify-tag">工作流</a-tag>
            <span v-if="!row.knowledgeBaseId && !row.workflowId" class="empty-dash">—</span>
          </div>
        </template>
        <template #action="{ row }">
          <div class="agent-action-cell">
            <a-button type="link" size="small" @click="openEdit(row)">编辑</a-button>
            <a-button type="link" danger size="small" class="agent-action-link" @click="onDelete(row)">删除</a-button>
          </div>
        </template>
      </HifyTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { PlusOutlined } from '@ant-design/icons-vue'
import HifyTable from '@/components/base/HifyTable.vue'
import { useConfirm } from '@/composables/useConfirm'
import type { TableColumn } from '@/components/base/HifyTable.vue'
import {
  getAgentList, deleteAgent,
  getModelOptions,
} from '@/api/agent'
import type { AgentListItem, ModelOption } from '@/api/agent'
import { formatAgentCreatedAt } from './agentList'

const agentTableRowStyle = { height: '3.25rem' }
const router = useRouter()

// ── 模型选项 ───────────────────────────────────────────────
const modelOptions = ref<ModelOption[]>([])
const modelsLoading = ref(false)
// modelConfigId → 模型名称，用于列表展示
const modelNameMap = computed(() => {
  const m: Record<number, string> = {}
  for (const opt of modelOptions.value) m[opt.modelConfigId] = opt.modelName
  return m
})

const loadModelOptions = async () => {
  modelsLoading.value = true
  try { modelOptions.value = await getModelOptions() } finally { modelsLoading.value = false }
}

onMounted(async () => {
  await loadModelOptions()
})

// ── 表格 ───────────────────────────────────────────────────
const tableRef = ref<InstanceType<typeof HifyTable>>()

const columns = computed<TableColumn[]>(() => [
  { label: '名称',     slot: 'name',        minWidth: '13.75rem' },
  { label: '关联模型', slot: 'modelName',   width: '10rem' },
  { label: '工具数',   prop: 'toolCount',   width: '5rem' },
  { label: '能力',     slot: 'bindings',    width: '7.5rem' },
  { label: 'Temperature', slot: 'temperature', width: '6.875rem' },
  { label: '状态',     slot: 'enabled',     width: '5rem' },
  { label: '创建时间', slot: 'createdAt',   width: '10.5rem', hideOnNarrow: true },
  { label: '操作',     slot: 'action',      width: '9.5rem' },
])

const fetchAgents = async ({ page, pageSize }: { page: number; pageSize: number }) => {
  const res = await getAgentList({ page, pageSize })
  return { list: res.list as unknown as Record<string, unknown>[], total: res.total }
}

const openCreate = () => {
  router.push({ name: 'HifyAgentNew' })
}

const openEdit = (row: AgentListItem) => {
  router.push({ name: 'HifyAgentWorkbench', params: { id: row.id } })
}

// ── 删除 ───────────────────────────────────────────────────
const { confirm } = useConfirm()

const onDelete = async (row: AgentListItem) => {
  await confirm(
    `确定删除 Agent「${row.name}」吗？`,
    async () => { await deleteAgent(row.id) },
    '删除成功'
  )
  tableRef.value?.refresh()
}
</script>

<style scoped>
.page-header { margin-bottom: var(--space-4); }

.agent-card :deep(.ant-table-thead > tr > th) {
  background-color: var(--color-bg-page);
}
.agent-card :deep(.ant-table-tbody > tr:hover > td) {
  background-color: var(--color-bg-hover) !important;
}
.agent-card :deep(.hify-table-pagination) {
  padding-top: var(--space-3);
  border-top: 0.0625rem solid var(--color-border-default);
  justify-content: flex-end;
}

.button-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.agent-name-cell,
.agent-model-cell,
.agent-time-cell {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.25rem;
}
.agent-name-cell {
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
}
.agent-model-cell,
.agent-time-cell {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}
.mono { font-family: monospace; font-size: var(--text-sm); }
.agent-action-cell {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  white-space: nowrap;
}
.agent-action-link {
  margin-left: 0;
}
.agent-dialog-form {
  margin-top: var(--space-3);
}
.agent-prompt-input {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}
.agent-number-input {
  width: 11.25rem;
}
.binding-tags {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 1.5rem;
}
.empty-dash {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

/* Slider 行 */
.slider-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  width: 100%;
}
.slider-val {
  font-family: monospace;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  min-width: 1.75rem;
  text-align: right;
}

/* form hint */
.form-hint {
  margin-left: 0.625rem;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* 工具绑定区 */
.tools-pane {
  padding: var(--space-4) var(--space-1);
  min-height: 10rem;
}
.tools-empty {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  text-align: center;
  padding: var(--space-10) 0;
}
.tools-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}
.tool-checkbox-item {
  height: auto;
  align-items: flex-start;
}
.tool-info {
  display: flex;
  flex-direction: column;
  gap: var(--radius-xs);
  line-height: 1.4;
}
.tool-name {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}
.tool-endpoint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-family: monospace;
}
</style>
