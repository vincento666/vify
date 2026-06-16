<template>
  <div class="page-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="page-header-left">
        <div class="page-title">模型提供商管理</div>
        <div class="page-desc">管理接入的 AI 模型提供商，配置 API Key 和连接信息</div>
      </div>
      <div class="page-header-actions">
        <button class="btn-primary" @click="dialogRef?.open()">
          <span class="button-icon"><PlusOutlined /></span>
          新增提供商
        </button>
      </div>
    </div>

    <!-- 列表 -->
    <div class="hify-card provider-card">
      <HifyTable
        :columns="columns"
        :api="fetchProviders"
        :row-style="providerTableRowStyle"
        ref="tableRef"
      >
        <!-- 启用状态列 -->
        <template #status="{ row }">
          <a-tag :color="row.enabled ? 'success' : 'default'" class="hify-tag">
            {{ row.enabled ? '启用' : '禁用' }}
          </a-tag>
        </template>
        <!-- 健康状态列 -->
        <template #health="{ row }">
          <template v-if="row.health">
            <a-tag :color="healthTagType(row.health.status)" class="hify-tag">
              {{ healthLabel(row.health.status) }}
            </a-tag>
            <span v-if="row.health.latencyMs != null" class="latency-ms">
              {{ row.health.latencyMs }}ms
            </span>
          </template>
          <a-tag v-else color="default" class="hify-tag">未知</a-tag>
        </template>
        <!-- 模型数列 -->
        <template #models="{ row }">
          <a-popover
            v-if="row.models && row.models.length > 0"
            placement="bottomLeft"
            trigger="click"
            :overlay-style="{ width: providerModelPopoverWidth }"
          >
            <template #content>
              <div class="model-list-popup">
                <div class="model-list-title">已配置模型（{{ row.models.length }} 个）</div>
                <div
                  v-for="m in row.models"
                  :key="m.id"
                  class="model-list-item"
                  :data-testid="`provider-model-row-${m.id}`"
                >
                  <div class="model-list-main">
                    <div class="model-list-line">
                      <span class="model-list-name">{{ m.displayName || m.modelId }}</span>
                      <a-tag :color="m.enabled ? 'success' : 'default'" class="hify-tag">
                        {{ m.enabled ? '启用' : '禁用' }}
                      </a-tag>
                    </div>
                    <div
                      v-if="modelTestResults[modelTestKey(row.id, m.id)]"
                      class="model-test-result"
                      :class="modelTestResults[modelTestKey(row.id, m.id)]?.ok ? 'success' : 'failure'"
                      :data-testid="`provider-model-test-result-${m.id}`"
                    >
                      <span class="status-icon">
                        <CheckCircleOutlined v-if="modelTestResults[modelTestKey(row.id, m.id)]?.ok" />
                        <CloseCircleOutlined v-else />
                      </span>
                      <span>{{ modelTestResultText(modelTestResults[modelTestKey(row.id, m.id)]!) }}</span>
                    </div>
                  </div>
                  <a-button
                    type="link"
                    size="small"
                    :loading="testingModelKey === modelTestKey(row.id, m.id)"
                    :disabled="!m.enabled"
                    :data-testid="`provider-model-test-${m.id}`"
                    @click.stop="onTestModelConnection(row, m)"
                  >测试</a-button>
                </div>
              </div>
            </template>
            <span class="model-count-link">{{ enabledModelCount(row) }} 个</span>
          </a-popover>
          <span v-else class="text-muted">0 个</span>
        </template>
        <!-- 操作列 -->
        <template #action="{ row }">
          <a-button type="link" size="small" @click="dialogRef?.open(row)">编辑</a-button>
          <a-button
            type="link" size="small"
            class="provider-action-link"
            :loading="testingId === row.id"
            @click="onTestConnection(row)"
          >测试</a-button>
          <a-button type="link" danger size="small" class="provider-action-link" @click="onDelete(row)">删除</a-button>
        </template>
      </HifyTable>
    </div>

    <!-- 新增/编辑弹窗 -->
    <HifyFormDialog
      ref="dialogRef"
      :title="dialogTitle"
      :rules="rules"
      width="32.5rem"
      label-width="6.25rem"
      @submit="onSubmit"
    >
      <template #default="{ form }">
        <a-form-item label="名称" name="name">
          <a-input v-model:value="form.name" placeholder="请输入提供商名称" />
        </a-form-item>
        <a-form-item label="类型" name="type">
          <a-select v-model:value="form.type" :options="providerTypes" placeholder="请选择类型" class="full-width-control" />
        </a-form-item>
        <a-form-item label="API Key">
          <a-input-password v-model:value="form.apiKey" placeholder="留空表示不修改" />
        </a-form-item>
        <a-form-item label="Base URL" name="baseUrl">
          <a-input v-model:value="form.baseUrl" placeholder="https://api.openai.com/v1" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="form.description" placeholder="可选" />
        </a-form-item>
      </template>
    </HifyFormDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { CheckCircleOutlined, CloseCircleOutlined, PlusOutlined } from '@ant-design/icons-vue'
import HifyTable from '@/components/base/HifyTable.vue'
import HifyFormDialog from '@/components/base/HifyFormDialog.vue'
import { useConfirm } from '@/composables/useConfirm'
import { notifyError, notifySuccess } from '@/utils/notify'
import type { TableColumn } from '@/components/base/HifyTable.vue'
import {
  getProviderList,
  createProvider,
  updateProvider,
  deleteProvider,
  testConnection,
  testProviderModelConnectivity,
} from '@/api/provider'
import type { ModelConfig, ModelConnectivityTestResult, ProviderVO, HealthStatus } from '@/api/provider'

type FormRules = Record<string, unknown>
const providerTableRowStyle = { height: '3.25rem' }
const providerModelPopoverWidth = '25rem'

const providerTypes = [
  { label: 'OpenAI',            value: 'OPENAI' },
  { label: 'Anthropic (Claude)', value: 'ANTHROPIC' },
  { label: 'Google Gemini',     value: 'GEMINI' },
  { label: 'Azure OpenAI',      value: 'AZURE_OPENAI' },
  { label: 'Ollama',            value: 'OLLAMA' },
  { label: 'OpenAI Compatible', value: 'OPENAI_COMPATIBLE' },
]

// ── API ────────────────────────────────────────────────────
const fetchProviders = async ({ page, pageSize }: { page: number; pageSize: number }) => {
  const res = await getProviderList({ page, pageSize })
  return { list: res.list as unknown as Record<string, unknown>[], total: res.total }
}

// ── 健康状态工具 ───────────────────────────────────────────
const healthTagType = (status: HealthStatus) => {
  const map: Record<HealthStatus, string> = {
    UP: 'success', DOWN: 'error', DEGRADED: 'warning', UNKNOWN: 'default',
  }
  return map[status] ?? 'default'
}
const healthLabel = (status: HealthStatus) => {
  const map: Record<HealthStatus, string> = {
    UP: '正常', DOWN: '故障', DEGRADED: '降级', UNKNOWN: '未知',
  }
  return map[status] ?? status
}
const enabledModelCount = (row: ProviderVO) =>
  row.models?.filter(m => m.enabled).length ?? 0

// ── 表格列配置 ─────────────────────────────────────────────
const columns = computed<TableColumn[]>(() => [
  { label: '名称',     prop: 'name',     minWidth: 140 },
  { label: '类型',     prop: 'type',     width: 140 },
  { label: 'Base URL', prop: 'baseUrl',  minWidth: 200, hideOnNarrow: true },
  { label: '状态',     slot: 'status',   width: 80 },
  { label: '健康',     slot: 'health',   width: 120 },
  { label: '模型数',   slot: 'models',   width: 80 },
  { label: '操作',     slot: 'action',   width: 160 },
])

// ── 弹窗 ───────────────────────────────────────────────────
const tableRef = ref<InstanceType<typeof HifyTable>>()
const dialogRef = ref<InstanceType<typeof HifyFormDialog>>()

const rules: FormRules = {
  name:    [{ required: true, message: '请输入名称',      trigger: 'blur' }],
  type:    [{ required: true, message: '请选择类型',      trigger: 'change' }],
  baseUrl: [{ required: true, message: '请输入 Base URL', trigger: 'blur' }],
}

const dialogTitle = computed(() => '提供商信息')

const onSubmit = async (data: Record<string, unknown>, mode: 'add' | 'edit') => {
  const apiKey = (data.apiKey as string) || ''
  if (mode === 'add') {
    await createProvider({
      name: data.name as string,
      type: data.type as any,
      baseUrl: data.baseUrl as string,
      description: data.description as string | undefined,
      authConfig: apiKey ? { api_key: apiKey } : {},
    })
  } else {
    const updateData: any = {
      name: data.name,
      baseUrl: data.baseUrl,
      description: data.description,
    }
    if (apiKey) updateData.authConfig = { api_key: apiKey }
    await updateProvider(data.id as number, updateData)
  }
  notifySuccess(mode === 'add' ? '新增成功' : '保存成功')
  dialogRef.value?.close()
  tableRef.value?.refresh()
}

// ── 删除 ───────────────────────────────────────────────────
const { confirm } = useConfirm()

const onDelete = async (row: ProviderVO) => {
  await confirm(
    `确定删除提供商「${row.name}」吗？`,
    async () => { await deleteProvider(row.id) },
    '删除成功'
  )
  tableRef.value?.refresh()
}

// ── 连通性测试 ─────────────────────────────────────────────
const testingId = ref<number | null>(null)
const testingModelKey = ref<string | null>(null)
const modelTestResults = ref<Record<string, ModelConnectivityTestResult>>({})

const onTestConnection = async (row: ProviderVO) => {
  testingId.value = row.id
  try {
    const result = await testConnection(row.id)
    if (result.success) {
      notifySuccess(`连接成功，延迟 ${result.latencyMs}ms，发现 ${result.modelCount} 个模型`)
    } else {
      notifyError(`连接失败：${result.errorMessage}`)
    }
  } finally {
    testingId.value = null
  }
}

const modelTestKey = (providerId: number, modelConfigId: number) =>
  `${providerId}:${modelConfigId}`

const onTestModelConnection = async (row: ProviderVO, model: ModelConfig) => {
  const key = modelTestKey(row.id, model.id)
  testingModelKey.value = key
  try {
    modelTestResults.value = {
      ...modelTestResults.value,
      [key]: await testProviderModelConnectivity(row.id, model.id),
    }
  } finally {
    testingModelKey.value = null
  }
}

const modelTestResultText = (result: ModelConnectivityTestResult) => {
  if (!result.ok) {
    return `连通性测试失败：${result.error || '未知错误'}`
  }
  return `连通性测试成功：${result.model} · ${result.elapsedMs}ms · total ${result.usage.totalTokens}`
}
</script>

<style scoped>
.page-header { margin-bottom: var(--space-4); }

.provider-card :deep(.ant-table-thead > tr > th) {
  background-color: var(--color-bg-page);
}
.provider-card :deep(.ant-table-tbody > tr:hover > td) {
  background-color: var(--color-bg-hover) !important;
}
.provider-card :deep(.hify-table-pagination) {
  padding-top: var(--space-3);
  border-top: 0.0625rem solid var(--color-border-default);
  justify-content: flex-end;
}

.button-icon,
.status-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.full-width-control {
  width: 100%;
}

.latency-ms {
  margin-left: 0.375rem;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.model-count-link {
  color: var(--color-primary);
  cursor: pointer;
  font-size: var(--text-sm);
}
.model-count-link:hover { text-decoration: underline; }

.text-muted {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.provider-action-link {
  margin-left: var(--space-1);
}

.model-list-popup { padding: var(--space-1) 0; }
.model-list-title {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
  padding-bottom: 0.375rem;
  border-bottom: 1px solid var(--color-border-default);
}
.model-list-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
}
.model-list-main {
  min-width: 0;
  flex: 1;
}
.model-list-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.model-list-name {
  min-width: 0;
  overflow-wrap: anywhere;
}
.model-test-result {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  line-height: 1.35;
}
.model-test-result.success { color: var(--color-success); }
.model-test-result.failure { color: var(--color-danger); }
</style>
