<template>
  <div class="page-container">
    <!-- 顶部导航 -->
    <div class="page-header">
      <div class="page-header-left">
        <a-button type="text" @click="router.push({ name: 'HifyMcp' })" class="back-btn">
          <span class="button-icon"><ArrowLeftOutlined /></span>
          返回
        </a-button>
        <div>
          <div class="page-title">{{ server?.name || '调试工具' }}</div>
          <div class="page-desc">{{ server?.endpoint }}</div>
        </div>
      </div>
      <div class="page-header-actions">
        <a-tag :color="connectionStatus === 'ok' ? 'success' : connectionStatus === 'fail' ? 'error' : 'default'" class="hify-tag">
          {{ connectionStatus === 'ok' ? '已连接' : connectionStatus === 'fail' ? '无法连接' : '未检测' }}
        </a-tag>
        <a-button size="small" class="refresh-tools-button" :loading="loadingTools" @click="loadTools">
          <span class="button-icon"><ReloadOutlined /></span>
          刷新工具
        </a-button>
      </div>
    </div>

    <div class="debug-layout">
      <!-- 左侧：工具选择 + 参数 -->
      <div class="left-panel">
        <!-- Server 信息卡 -->
        <div class="info-card">
          <div class="info-title">Server 信息</div>
          <div class="info-row">
            <span class="info-label">名称</span>
            <span class="info-value">{{ server?.name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Endpoint</span>
            <span class="info-value mono">{{ server?.endpoint }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">描述</span>
            <span class="info-value">{{ server?.description || '—' }}</span>
          </div>
        </div>

        <!-- 工具列表 / 手动输入 -->
        <div class="panel-card">
          <div class="panel-card-header">
            <span class="panel-card-title">选择工具</span>
            <a-button type="text" size="small" @click="manualMode = !manualMode">
              {{ manualMode ? '从列表选择' : '手动输入' }}
            </a-button>
          </div>

          <!-- 手动输入模式 -->
          <div v-if="manualMode" class="tool-input-wrap">
            <a-input
              v-model:value="toolName"
              placeholder="输入工具名，如 refund_order"
              clearable
            />
          </div>

          <!-- 工具列表模式 -->
          <div v-else>
            <div v-if="loadingTools" class="tool-loading">
              <a-skeleton :paragraph="{ rows: 3 }" active />
            </div>
            <div v-else-if="tools.length === 0" class="tool-empty">
              <span class="status-icon warning"><WarningFilled /></span>
              <span>无法获取工具列表，可切换为手动输入</span>
            </div>
            <div v-else class="tool-list">
              <div
                v-for="tool in tools"
                :key="tool.name"
                class="tool-item"
                :class="{ active: toolName === tool.name }"
                @click="selectTool(tool)"
              >
                <span class="ti-icon"><ToolOutlined /></span>
                <div class="ti-info">
                  <div class="ti-name">{{ tool.name }}</div>
                  <div class="ti-desc">{{ tool.description || '无描述' }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 参数面板 -->
        <div class="panel-card">
          <div class="panel-card-header">
            <span class="panel-card-title">输入参数</span>
            <a-button type="text" size="small" @click="paramMode = paramMode === 'form' ? 'json' : 'form'">
              {{ paramMode === 'form' ? 'JSON 模式' : '表单模式' }}
            </a-button>
          </div>

          <!-- 表单模式 -->
          <div v-if="paramMode === 'form'">
            <div v-if="paramEntries.length === 0" class="param-hint">
              <span v-if="!selectedTool && !manualMode">请先选择工具</span>
              <span v-else>该工具无需参数</span>
            </div>
            <div v-else class="param-form">
              <div v-for="param in paramEntries" :key="param.name" class="param-row">
                <div class="param-label-row">
                  <span class="param-name">{{ param.name }}</span>
                  <a-tag v-if="param.required" color="error" class="hify-tag">必填</a-tag>
                  <a-tag class="hify-tag">{{ param.type }}</a-tag>
                </div>
                <div v-if="param.description" class="param-desc">{{ param.description }}</div>
                <a-input-number
                  v-if="param.type === 'number' || param.type === 'integer'"
                  v-model:value="formValues[param.name]"
                  :placeholder="param.name"
                  class="full-width-control"
                />
                <a-input
                  v-else
                  v-model:value="formValues[param.name]"
                  :placeholder="param.description || param.name"
                />
              </div>
            </div>
          </div>

          <!-- JSON 模式 -->
          <div v-else>
            <a-textarea
              v-model:value="jsonArgs"
              :rows="6"
              placeholder='{"param1": "value1"}'
              class="json-args-input"
            />
            <div v-if="jsonError" class="json-error">{{ jsonError }}</div>
          </div>
        </div>

        <!-- 执行按钮 -->
        <a-button
          type="primary"
          size="large"
          :loading="calling"
          :disabled="!toolName.trim()"
          @click="callTool"
          class="full-width-control"
        >
          <span class="button-icon"><PlayCircleOutlined /></span>
          执行调用
        </a-button>
      </div>

      <!-- 右侧：结果 -->
      <div class="right-panel">
        <div class="panel-card result-panel">
          <div class="panel-card-header">
            <span class="panel-card-title">调用结果</span>
            <span v-if="history.length" class="history-count">{{ history.length }} 条记录</span>
          </div>

          <div v-if="history.length === 0" class="result-empty">
            <span class="result-empty-icon"><PlayCircleOutlined /></span>
            <p>填写参数后点击「执行调用」</p>
          </div>

          <div v-else class="history-list">
            <div
              v-for="(item, idx) in history"
              :key="idx"
              class="history-item"
              :class="{ 'is-error': !item.success, 'is-active': idx === 0 }"
            >
              <!-- 头部 -->
              <div class="hi-header">
                <div class="hi-status">
                  <span v-if="item.success" class="status-icon ok"><CheckCircleOutlined /></span>
                  <span v-else class="status-icon err"><CloseCircleOutlined /></span>
                  <span class="hi-tool">{{ item.toolName }}</span>
                </div>
                <div class="hi-meta">
                  <a-tag :color="item.success ? 'success' : 'error'" class="hify-tag">
                    {{ item.elapsedMs }}ms
                  </a-tag>
                  <span class="hi-time">{{ item.time }}</span>
                </div>
              </div>

              <!-- 参数 -->
              <div class="hi-section">
                <div class="hi-label">参数</div>
                <code class="hi-args">{{ JSON.stringify(item.arguments) }}</code>
              </div>

              <!-- 结果 -->
              <div class="hi-section">
                <div class="hi-label">{{ item.success ? '返回结果' : '错误信息' }}</div>
                <pre class="hi-result" :class="{ 'hi-result--error': !item.success }">{{ item.success ? item.result : item.errorMessage }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  ToolOutlined,
  WarningFilled,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { getMcpServerDetail, getMcpServerTools, debugMcpTool } from '@/api/mcp'
import type { McpToolDetail, McpServerVO } from '@/api/mcp'

const route = useRoute()
const router = useRouter()
const serverId = Number(route.params.id)

// ── 服务器信息 ──────────────────────────────────────────────
const server = ref<McpServerVO | null>(null)

// ── 工具列表 ─────────────────────────────────────────────────
const tools = ref<McpToolDetail[]>([])
const loadingTools = ref(false)
const connectionStatus = ref<'unknown' | 'ok' | 'fail'>('unknown')
const manualMode = ref(false)

// ── 选中工具 ─────────────────────────────────────────────────
const toolName = ref('')
const selectedTool = ref<McpToolDetail | null>(null)

// ── 参数 ─────────────────────────────────────────────────────
const paramMode = ref<'form' | 'json'>('form')
const formValues = ref<Record<string, unknown>>({})
const jsonArgs = ref('{}')
const jsonError = ref('')

// ── 调用历史 ─────────────────────────────────────────────────
interface HistoryItem {
  toolName: string
  time: string
  success: boolean
  result: string | null
  errorMessage: string | null
  elapsedMs: number
  arguments: Record<string, unknown>
}
const history = ref<HistoryItem[]>([])
const calling = ref(false)

// ── 计算参数列表（从选中工具的 schema 提取）──────────────────
const paramEntries = computed(() => {
  if (!selectedTool.value?.inputSchema?.properties) return []
  const required = selectedTool.value.requiredParams ?? []
  return Object.entries(selectedTool.value.inputSchema.properties).map(([name, schema]) => ({
    name,
    type: (schema as any).type ?? 'string',
    description: (schema as any).description as string | undefined,
    required: required.includes(name),
  }))
})

// ── 操作 ─────────────────────────────────────────────────────
const selectTool = (tool: McpToolDetail) => {
  selectedTool.value = tool
  toolName.value = tool.name
  formValues.value = {}
  jsonArgs.value = '{}'
}

const loadTools = async () => {
  loadingTools.value = true
  try {
    const list = await getMcpServerTools(serverId)
    tools.value = list
    if (list.length > 0) {
      connectionStatus.value = 'ok'
      if (!toolName.value) selectTool(list[0])
    } else {
      // 连不上时后端返回空列表
      connectionStatus.value = 'fail'
      manualMode.value = true
    }
  } catch {
    connectionStatus.value = 'fail'
    manualMode.value = true
  } finally {
    loadingTools.value = false
  }
}

const buildArguments = (): Record<string, unknown> | null => {
  if (paramMode.value === 'json') {
    try {
      jsonError.value = ''
      return JSON.parse(jsonArgs.value || '{}')
    } catch {
      jsonError.value = 'JSON 格式错误'
      return null
    }
  }
  return { ...formValues.value }
}

const callTool = async () => {
  if (!toolName.value.trim()) return

  // 必填校验（表单模式）
  if (paramMode.value === 'form') {
    for (const param of paramEntries.value) {
      if (param.required && (formValues.value[param.name] === undefined || formValues.value[param.name] === '')) {
        message.warning(`参数「${param.name}」不能为空`)
        return
      }
    }
  }

  const args = buildArguments()
  if (args === null) return

  calling.value = true
  try {
    const res = await debugMcpTool(serverId, { toolName: toolName.value.trim(), arguments: args })
    history.value.unshift({
      toolName: toolName.value.trim(),
      time: new Date().toLocaleTimeString(),
      success: res.success,
      result: res.result,
      errorMessage: res.errorMessage,
      elapsedMs: res.elapsedMs,
      arguments: args,
    })
    if (history.value.length > 5) history.value.pop()
  } finally {
    calling.value = false
  }
}

onMounted(async () => {
  try {
    server.value = await getMcpServerDetail(serverId)
  } catch {
    message.error('获取 Server 信息失败')
  }
  await loadTools()
})
</script>

<style scoped>
.back-btn {
  color: var(--color-text-secondary);
  margin-right: 0.25rem;
  padding: 0;
}

.button-icon,
.status-icon,
.result-empty-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.refresh-tools-button {
  margin-left: var(--space-2);
}

/* ── 整体布局 ──────────────────────────────────────────────── */
.debug-layout {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.left-panel {
  width: 22.5rem;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.right-panel {
  flex: 1;
  min-width: 0;
}

/* ── 卡片 ──────────────────────────────────────────────────── */
.info-card,
.panel-card {
  background: var(--color-bg-card);
  border: 0.0625rem solid var(--color-border-default);
  border-radius: 0.625rem;
  padding: 1rem;
}

.info-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-tertiary);
  margin-bottom: 0.625rem;
}

.info-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.375rem;
  align-items: flex-start;
}
.info-label {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
  width: 3rem;
  flex-shrink: 0;
  padding-top: 0.0625rem;
}
.info-value {
  font-size: 0.8125rem;
  color: var(--color-text-primary);
  word-break: break-all;
}
.info-value.mono {
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.panel-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}
.panel-card-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

/* ── 工具列表 ──────────────────────────────────────────────── */
.tool-loading { padding: 0.25rem 0; }

.tool-empty {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
  padding: 0.5rem 0;
}
.tool-empty .warning { color: var(--color-warning); }

.tool-input-wrap { padding: 0.25rem 0; }

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  max-height: 13.75rem;
  overflow-y: auto;
}

.tool-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem 0.625rem;
  border-radius: 0.375rem;
  cursor: pointer;
  border: 0.0625rem solid transparent;
  transition: background 0.15s;
}
.tool-item:hover { background: var(--color-bg-hover); }
.tool-item.active {
  background: rgba(99,102,241,0.08);
  border-color: rgba(99,102,241,0.25);
}

.ti-icon {
  flex-shrink: 0;
  margin-top: 0.125rem;
  color: var(--color-primary);
  font-size: 0.875rem;
}
.ti-info { overflow: hidden; }
.ti-name {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-primary);
  font-family: monospace;
}
.ti-desc {
  font-size: 0.6875rem;
  color: var(--color-text-tertiary);
  margin-top: 0.125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 参数面板 ──────────────────────────────────────────────── */
.param-hint {
  font-size: 0.8125rem;
  color: var(--color-text-tertiary);
  padding: 0.25rem 0 0.5rem;
}

.param-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.param-row { display: flex; flex-direction: column; gap: 0.3125rem; }

.param-label-row {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.param-name {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-primary);
  font-family: monospace;
}

.param-desc {
  font-size: 0.6875rem;
  color: var(--color-text-tertiary);
}

.json-error {
  font-size: 0.75rem;
  color: var(--color-danger);
  margin-top: 0.25rem;
}

.json-args-input :deep(textarea) {
  font-family: monospace;
  font-size: 0.8125rem;
}

/* ── 结果面板 ──────────────────────────────────────────────── */
.result-panel {
  min-height: 25rem;
}

.result-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3.75rem 0;
  gap: 0.75rem;
  color: var(--color-text-tertiary);
  font-size: 0.875rem;
}

.result-empty-icon {
  font-size: 2.25rem;
  opacity: 0.4;
}

.history-count {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.history-item {
  border: 0.0625rem solid var(--color-border-default);
  border-radius: 0.5rem;
  padding: 0.875rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  transition: border-color 0.2s;
}
.history-item.is-active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 0.125rem rgba(99,102,241,0.08);
}
.history-item.is-error {
  border-color: rgba(239,68,68,0.3);
}

.hi-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.hi-status {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}
.status-icon { font-size: 1rem; }
.status-icon.ok  { color: var(--color-success); }
.status-icon.err { color: var(--color-danger); }
.hi-tool {
  font-size: 0.875rem;
  font-weight: 600;
  font-family: monospace;
  color: var(--color-text-primary);
}
.hi-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.hi-time {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.hi-section { display: flex; flex-direction: column; gap: 0.25rem; }
.hi-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-tertiary);
}
.hi-args {
  font-size: 0.75rem;
  font-family: monospace;
  color: var(--color-text-secondary);
  word-break: break-all;
  background: var(--color-bg-page);
  padding: 0.375rem 0.5rem;
  border-radius: 0.25rem;
}
.hi-result {
  margin: 0;
  font-size: 0.8125rem;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--color-text-primary);
  background: var(--color-bg-page);
  padding: 0.625rem 0.75rem;
  border-radius: 0.375rem;
  max-height: 18.75rem;
  overflow-y: auto;
  line-height: 1.6;
}
.hi-result--error {
  color: var(--color-danger);
  background: rgba(239,68,68,0.05);
}

.full-width-control {
  width: 100%;
}
</style>
