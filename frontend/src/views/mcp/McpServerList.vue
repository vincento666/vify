<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-left">
        <div class="page-title">MCP 工具服务</div>
        <div class="page-desc">管理 MCP Server，让 Agent 能调用外部系统（订单、物流、工单等）</div>
      </div>
      <div class="page-header-actions">
        <button class="btn-primary" @click="dialogRef?.open()">
          <span class="button-icon"><PlusOutlined /></span>
          新增 Server
        </button>
      </div>
    </div>

    <div class="hify-card">
      <HifyTable
        :columns="columns"
        :api="fetchServers"
        ref="tableRef"
      >
        <!-- 状态 -->
        <template #status="{ row }">
          <a-tag :color="row.enabled ? 'success' : 'default'" class="hify-tag">
            {{ row.enabled ? '启用' : '禁用' }}
          </a-tag>
        </template>

        <!-- endpoint -->
        <template #endpoint="{ row }">
          <span class="endpoint-text" :title="row.endpoint">{{ row.endpoint }}</span>
        </template>

        <!-- 操作 -->
        <template #action="{ row }">
          <a-button type="link" size="small" @click="dialogRef?.open({ ...row, enabledBool: Boolean(row.enabled) })">编辑</a-button>
          <a-button
            type="link" size="small"
            class="mcp-action-link"
            :loading="testingId === row.id"
            @click="onTest(row)"
          >测试</a-button>
          <a-button
            type="link" size="small"
            class="mcp-action-link"
            @click="router.push({ name: 'HifyMcpDebug', params: { id: row.id } })"
          >调试</a-button>
          <a-button
            type="link" danger size="small"
            class="mcp-action-link"
            @click="onDelete(row)"
          >删除</a-button>
        </template>
      </HifyTable>
    </div>

    <!-- 测试结果抽屉 -->
    <a-drawer v-model:open="testDrawerVisible" title="连通测试结果" width="25rem" placement="right">
      <template v-if="testResult">
        <div v-if="testResult.success" class="test-success">
          <span class="test-icon success"><CheckCircleOutlined /></span>
          <div class="test-meta">连接成功，延迟 {{ testResult.latencyMs }}ms</div>
          <div class="tool-list-title">发现 {{ testResult.tools?.length ?? 0 }} 个工具</div>
          <div v-if="testResult.tools?.length" class="tool-list">
            <div v-for="t in testResult.tools" :key="t" class="tool-item">
              <span class="tool-icon"><ToolOutlined /></span>
              <span>{{ t }}</span>
            </div>
          </div>
          <div v-else class="no-tools">该 Server 暂未声明工具</div>
        </div>
        <div v-else class="test-fail">
          <span class="test-icon fail"><CloseCircleOutlined /></span>
          <div class="test-meta">连接失败</div>
          <div class="error-msg">{{ testResult.errorMessage }}</div>
        </div>
      </template>
    </a-drawer>

    <!-- 新增/编辑弹窗 -->
    <HifyFormDialog
      ref="dialogRef"
      title="MCP Server 信息"
      :rules="rules"
      width="31.25rem"
      label-width="5.625rem"
      @submit="onSubmit"
    >
      <template #default="{ form }">
        <a-form-item label="名称" name="name">
          <a-input v-model:value="form.name" placeholder="如：订单服务" />
        </a-form-item>
        <a-form-item label="Endpoint" name="endpoint">
          <a-input v-model:value="form.endpoint" placeholder="http://localhost:9001/mcp" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="form.description" placeholder="可选" />
        </a-form-item>
        <a-form-item v-if="form.id" label="状态">
          <a-switch
            v-model:checked="form.enabledBool"
            checked-children="启用"
            un-checked-children="禁用"
          />
        </a-form-item>
      </template>
    </HifyFormDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { CheckCircleOutlined, CloseCircleOutlined, PlusOutlined, ToolOutlined } from '@ant-design/icons-vue'
import HifyTable from '@/components/base/HifyTable.vue'
import HifyFormDialog from '@/components/base/HifyFormDialog.vue'
import { useConfirm } from '@/composables/useConfirm'
import { notifySuccess } from '@/utils/notify'
import type { TableColumn } from '@/components/base/HifyTable.vue'
import {
  getMcpServerList,
  createMcpServer,
  updateMcpServer,
  deleteMcpServer,
  testMcpServer,
} from '@/api/mcp'
import type { McpServerVO, McpTestResult } from '@/api/mcp'

type FormRules = Record<string, unknown>
const router = useRouter()

// ── 表格 ───────────────────────────────────────────────────
const tableRef = ref<InstanceType<typeof HifyTable>>()

const columns = computed<TableColumn[]>(() => [
  { label: '名称',     prop: 'name',     minWidth: '8.75rem' },
  { label: 'Endpoint', slot: 'endpoint', minWidth: '13.75rem' },
  { label: '描述',     prop: 'description', minWidth: '10rem', hideOnNarrow: true },
  { label: '状态',     slot: 'status',   width: '5rem' },
  { label: '操作',     slot: 'action',   width: '11.25rem' },
])

const fetchServers = async ({ page, pageSize }: { page: number; pageSize: number }) => {
  const res = await getMcpServerList({ page, pageSize })
  return { list: res.list as unknown as Record<string, unknown>[], total: res.total }
}

// ── 弹窗 ───────────────────────────────────────────────────
const dialogRef = ref<InstanceType<typeof HifyFormDialog>>()

const rules: FormRules = {
  name:     [{ required: true, message: '请输入名称',     trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入 Endpoint', trigger: 'blur' }],
}

const onSubmit = async (data: Record<string, unknown>, mode: 'add' | 'edit') => {
  if (mode === 'add') {
    await createMcpServer({
      name: data.name as string,
      endpoint: data.endpoint as string,
      description: data.description as string | undefined,
    })
  } else {
    await updateMcpServer(data.id as number, {
      name: data.name as string,
      endpoint: data.endpoint as string,
      description: data.description as string | undefined,
      enabled: (data.enabledBool as boolean) ? 1 : 0,
    })
  }
  notifySuccess(mode === 'add' ? '新增成功' : '保存成功')
  dialogRef.value?.close()
  tableRef.value?.refresh()
}

// ── 删除 ───────────────────────────────────────────────────
const { confirm } = useConfirm()

const onDelete = async (row: McpServerVO) => {
  await confirm(
    `确定删除「${row.name}」吗？`,
    async () => { await deleteMcpServer(row.id) },
    '删除成功'
  )
  tableRef.value?.refresh()
}

// ── 连通测试 ────────────────────────────────────────────────
const testingId = ref<number | null>(null)
const testDrawerVisible = ref(false)
const testResult = ref<McpTestResult | null>(null)

const onTest = async (row: McpServerVO) => {
  testingId.value = row.id
  try {
    const result = await testMcpServer(row.id)
    testResult.value = result
    testDrawerVisible.value = true
  } finally {
    testingId.value = null
  }
}
</script>

<style scoped>
.endpoint-text {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  max-width: 17.5rem;
}

.mcp-action-link {
  margin-left: var(--space-1);
}

.button-icon,
.tool-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* ── 测试结果 ─────────────────────────────────────────────── */
.test-success,
.test-fail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6) 0;
}

.test-icon {
  font-size: 3rem;
  display: inline-flex;
}
.test-icon.success { color: var(--color-success); }
.test-icon.fail    { color: var(--color-danger); }

.test-meta {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--color-text-primary);
}

.tool-list-title {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  align-self: flex-start;
  width: 100%;
  padding-bottom: var(--space-2);
  border-bottom: 0.0625rem solid var(--color-border-default);
}

.tool-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.tool-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0.375rem 0.625rem;
  border-radius: var(--radius-sm);
  background: var(--color-bg-page);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.tool-icon {
  color: var(--color-primary);
}

.no-tools {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.error-msg {
  font-size: var(--text-sm);
  color: var(--color-danger);
  text-align: center;
  padding: 0 var(--space-4);
  word-break: break-all;
}
</style>
