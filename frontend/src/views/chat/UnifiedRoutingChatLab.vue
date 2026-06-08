<template>
  <div class="runtime-lab-layout" data-testid="runtime-lab-chat">
    <aside class="lab-rail">
      <section class="lab-panel">
        <div class="panel-heading">
          <Connection class="panel-heading-icon" />
          <span>系统</span>
        </div>
        <div class="system-stack">
          <button type="button" class="system-option active">
            <span class="system-title">统一路由实验</span>
            <span class="system-meta">runtime-lab</span>
          </button>
          <button type="button" class="system-option" @click="openOrdinaryChat">
            <span class="system-title">普通对话</span>
            <span class="system-meta">/chat</span>
          </button>
        </div>
        <div class="session-actions">
          <el-button size="small" :icon="Refresh" :loading="creatingSession" @click="createFreshSession">
            新会话
          </el-button>
          <span class="session-id">{{ sessionId ? `#${sessionId}` : '未连接' }}</span>
        </div>
        <div class="runtime-config" data-testid="runtime-lab-config">
          <div class="runtime-config-row">
            <span>Chatflow</span>
            <strong>{{ configSummary.bindingLabel }}</strong>
          </div>
          <div class="runtime-config-row">
            <span>仲裁</span>
            <strong>{{ configSummary.arbitratorLabel }}</strong>
          </div>
          <div class="runtime-config-row">
            <span>密钥</span>
            <strong>{{ configSummary.secretLabel }}</strong>
          </div>
          <div class="runtime-config-row">
            <span>状态</span>
            <strong>{{ runtimeConfigLoading ? '加载中' : configSummary.availableLabel }}</strong>
          </div>
          <details class="runtime-binding-details">
            <summary>绑定明细</summary>
            <div v-if="configSummary.bindingRows.length === 0" class="muted-line">暂无 Chatflow 绑定</div>
            <div v-for="row in configSummary.bindingRows" :key="row" class="runtime-binding-row">
              {{ row }}
            </div>
          </details>
        </div>
      </section>

      <section class="lab-panel">
        <div class="panel-heading panel-heading-between">
          <span class="panel-heading-title">
            <ChatLineRound class="panel-heading-icon" />
            <span>意图样例</span>
          </span>
          <span class="scope-toolbar">
            <el-button
              size="small"
              :icon="Setting"
              data-testid="scope-config-open"
              @click="scopeDialogVisible = true"
            >
              接入
            </el-button>
            <el-switch
              v-model="showIntentSamples"
              class="samples-toggle"
              size="small"
              inline-prompt
              active-text="开"
              inactive-text="关"
              aria-label="显示意图样例"
              data-testid="intent-samples-toggle"
            />
          </span>
        </div>
        <div v-if="showIntentSamples" class="scope-summary">
          <span>已接通 {{ enabledScenarioIds.length }}/{{ boundScenarios.length }}</span>
          <span class="scope-actions">
            <button type="button" class="scope-action" @click="selectAllScenarios">全选</button>
            <button type="button" class="scope-action" @click="clearScenarios">清空</button>
          </span>
        </div>
        <div v-if="showIntentSamples" class="enabled-scope-list">
          <div v-if="runtimeConfigLoading" class="muted-line">正在加载 Chatflow 绑定</div>
          <div v-else-if="boundScenarios.length === 0" class="muted-line">暂无可接入 Chatflow SOP</div>
          <button
            v-for="scenario in enabledScenarios"
            :key="scenario.id"
            type="button"
            class="enabled-scope-chip"
            :disabled="!scenario.exists"
            @click="openChatflowCanvas(scenario.canvasPath)"
          >
            <span class="sop-short">{{ scenario.shortLabel }}</span>
            <span class="sop-label">{{ scenario.label }}</span>
          </button>
        </div>
      </section>

      <section v-if="showIntentSamples" class="lab-panel">
        <div class="panel-heading">触发样例</div>
        <div class="sample-stack">
          <div v-if="triggerSamples.length === 0" class="muted-line">未接通意图</div>
          <button
            v-for="sample in triggerSamples"
            :key="sample.key"
            type="button"
            class="sample-chip"
            :disabled="sending"
            @click="sendMessage(sample.text)"
          >
            <span class="sample-chip-tag">{{ sample.shortLabel }}</span>
            <span>{{ sample.text }}</span>
          </button>
        </div>
      </section>

      <section v-if="showIntentSamples" class="lab-panel">
        <div class="panel-heading">流程回复</div>
        <div class="sample-stack">
          <div v-if="replySamples.length === 0" class="muted-line">未接通意图</div>
          <button
            v-for="sample in replySamples"
            :key="sample.key"
            type="button"
            class="sample-chip"
            :disabled="sending"
            @click="sendMessage(sample.text)"
          >
            <span class="sample-chip-tag">{{ sample.shortLabel }}</span>
            <span>{{ sample.text }}</span>
          </button>
        </div>
      </section>
    </aside>

    <main class="lab-chat">
      <header class="lab-chat-header">
        <div>
          <h1>统一路由对话</h1>
          <p>自由对话 · {{ routeScopeLabel }} · {{ lastRouteAction }}</p>
        </div>
        <div class="lab-header-actions">
          <el-button
            size="small"
            :icon="Refresh"
            :loading="creatingSession"
            data-testid="runtime-lab-reset"
            @click="createFreshSession"
          >
            清空会话
          </el-button>
          <el-tag size="small" :type="sessionId ? 'success' : 'info'" effect="light">
            {{ sessionId ? 'Runtime Ready' : 'Waiting' }}
          </el-tag>
        </div>
      </header>

      <div ref="messagesEl" class="lab-messages">
        <div v-if="transcript.length === 0" class="empty-state">
          <ChatDotRound class="empty-icon" />
          <span>等待自由对话</span>
        </div>
        <div
          v-for="message in transcript"
          :key="message.id"
          class="lab-message"
          :class="message.role"
        >
          <div class="message-avatar">{{ message.role === 'user' ? '我' : 'AI' }}</div>
          <div class="message-body">
            <div v-if="message.pending" class="typing-indicator" data-testid="runtime-lab-typing">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div v-else class="message-content">{{ message.content }}</div>
            <div v-if="message.routeAction" class="message-meta">
              <el-tag size="small" effect="plain">{{ message.routeAction }}</el-tag>
              <span v-if="message.targetSopId">{{ message.targetSopId }}</span>
              <span v-if="message.taskSummary">{{ message.taskSummary }}</span>
            </div>
            <div v-if="message.resumePrompt" class="resume-prompt">
              {{ message.resumePrompt }}
            </div>
          </div>
        </div>
      </div>

      <form class="lab-composer" @submit.prevent="sendInput">
        <el-input
          v-model="inputText"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="输入消息"
          resize="none"
          :disabled="sending"
          data-testid="runtime-lab-input"
          @keydown.enter.exact.prevent="sendInput"
        />
        <el-button
          class="send-button"
          type="primary"
          :disabled="!inputText.trim() || sending"
          :loading="sending"
          data-testid="runtime-lab-send"
          @click="sendInput"
        >
          发送
        </el-button>
      </form>
    </main>

    <aside class="lab-inspector">
      <section class="lab-panel">
        <div class="panel-heading">路由</div>
        <dl class="decision-list">
          <div>
            <dt>action</dt>
            <dd data-testid="route-action">{{ latestTurn?.routeDecision.action ?? '-' }}</dd>
          </div>
          <div>
            <dt>target</dt>
            <dd>{{ latestTurn?.routeDecision.targetSopId ?? '-' }}</dd>
          </div>
          <div>
            <dt>funnel</dt>
            <dd data-testid="route-funnel">{{ funnelSummary.stageLabel }}</dd>
          </div>
          <div>
            <dt>source</dt>
            <dd data-testid="route-source">{{ funnelSummary.sourceLabel }}</dd>
          </div>
          <div>
            <dt>arbitrator</dt>
            <dd data-testid="route-arbitrator">{{ funnelSummary.arbitratorLabel }}</dd>
          </div>
          <div>
            <dt>reason</dt>
            <dd>{{ latestTurn?.routeDecision.reason ?? '-' }}</dd>
          </div>
        </dl>
      </section>

      <section class="lab-panel" data-testid="chatflow-trace-panel">
        <div class="panel-heading panel-heading-between">
          <span>Chatflow 轨迹</span>
          <span v-if="traceLoading" class="trace-loading">
            <span class="mini-spinner"></span>
            运行中
          </span>
        </div>
        <div v-if="chatflowTraceCards.length === 0" class="muted-line">暂无 Chatflow 运行</div>
        <div v-for="card in chatflowTraceCards" :key="card.taskId" class="trace-card">
          <div class="trace-card-head">
            <div>
              <strong>{{ card.chatflowName || card.sopId }}</strong>
              <span>{{ card.status }} · {{ card.completedCountLabel }}</span>
            </div>
            <el-button
              v-if="card.debugPath"
              size="small"
              plain
              @click="openChatflowDebug(card.debugPath)"
            >
              调试
            </el-button>
          </div>
          <div class="trace-current">
            当前节点：<span>{{ card.currentNodeLabel }}</span>
          </div>
          <div class="trace-node-list">
            <div
              v-for="node in card.nodes"
              :key="node.nodeKey"
              class="trace-node"
              :class="[`trace-node-${node.status.toLowerCase()}`, { current: node.current }]"
            >
              <span class="trace-node-icon" aria-hidden="true">
                <span v-if="node.current && ['RUNNING', 'WAITING', 'INTERRUPTED'].includes(node.status)" class="mini-spinner"></span>
                <span v-else-if="['SUCCEEDED', 'COMPLETED', 'DONE'].includes(node.status)">✓</span>
                <span v-else></span>
              </span>
              <span class="trace-node-main">
                <span>{{ node.nodeKey }} · {{ node.name }}</span>
                <small>{{ node.nodeType }} · {{ node.status }} · {{ node.elapsedMs }}ms</small>
              </span>
            </div>
          </div>
          <div class="slot-list">
            <div v-if="card.slotRows.length === 0" class="muted-line">暂无槽值</div>
            <div v-for="slot in card.slotRows" :key="slot.key" class="slot-row">
              <span>{{ slot.key }}</span>
              <strong>{{ slot.value }}</strong>
            </div>
          </div>
        </div>
      </section>

      <section class="lab-panel">
        <div class="panel-heading">任务</div>
        <div class="task-stack">
          <div v-if="tasks.length === 0" class="muted-line">暂无任务</div>
          <div v-for="task in tasks" :key="task.id" class="task-row">
            <span>{{ task.sopId }}</span>
            <el-tag size="small" effect="plain">{{ task.status }}</el-tag>
          </div>
        </div>
        <div v-if="latestTurn?.resumeOffer" class="resume-box">
          {{ latestTurn.resumeOffer.prompt ?? '可恢复暂停任务' }}
        </div>
      </section>

      <section class="lab-panel">
        <div class="panel-heading">事件</div>
        <div class="event-list">
          <div v-if="events.length === 0" class="muted-line">暂无事件</div>
          <div v-for="event in events.slice(-6)" :key="event.id" class="event-row">
            <span class="event-seq">#{{ event.sequence }}</span>
            <span>{{ event.eventType }}</span>
          </div>
        </div>
      </section>
    </aside>

    <el-dialog
      v-model="scopeDialogVisible"
      title="选择接入的 Chatflow SOP"
      width="42rem"
      align-center
      class="scope-dialog"
    >
      <div class="scope-dialog-body" data-testid="scope-dialog">
        <div class="scope-summary dialog-summary">
          <span>当前接入 {{ enabledScenarioIds.length }}/{{ boundScenarios.length }}</span>
          <span class="scope-actions">
            <button type="button" class="scope-action" @click="selectAllScenarios">全选</button>
            <button type="button" class="scope-action" @click="clearScenarios">清空</button>
          </span>
        </div>
        <div class="sop-list">
          <div v-if="boundScenarios.length === 0" class="muted-line">后台配置里暂无 Chatflow 绑定</div>
          <div
            v-for="scenario in boundScenarios"
            :key="scenario.id"
            class="sop-option sop-dialog-option"
            :class="{ active: isScenarioEnabled(scenario.id), missing: !scenario.exists }"
            :data-testid="`sop-option-${scenario.id}`"
          >
            <input
              type="checkbox"
              class="sop-checkbox"
              :checked="isScenarioEnabled(scenario.id)"
              :data-testid="`sop-toggle-${scenario.id}`"
              @change="setScenarioEnabledFromEvent(scenario.id, $event)"
            />
            <span class="sop-short">{{ scenario.shortLabel }}</span>
            <span class="sop-dialog-main">
              <span class="sop-label">{{ scenario.label }}</span>
              <small>#{{ scenario.chatflowId }} · {{ scenario.chatflowName || '未找到 Chatflow' }}</small>
            </span>
            <el-button
              size="small"
              plain
              :disabled="!scenario.exists"
              @click.stop="openChatflowCanvas(scenario.canvasPath)"
            >
              画布
            </el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  ChatLineRound,
  Connection,
  Refresh,
  Setting,
} from '@element-plus/icons-vue'
import {
  createRuntimeLabSession,
  getRuntimeLabChatflowTrace,
  getRuntimeLabConfig,
  listRuntimeLabEvents,
  listRuntimeLabTasks,
  postRuntimeLabMessage,
} from '@/api/runtimeLab'
import type {
  RuntimeLabChatflowTrace,
  RuntimeLabConfig,
  RuntimeLabEvent,
  RuntimeLabTask,
  RuntimeLabTurn,
} from '@/api/runtimeLab'
import {
  AIRLINE_SOP_SCENARIOS,
  buildRuntimeLabBoundScenarios,
  buildRuntimeLabConfigSummary,
  buildRuntimeLabFunnelSummary,
  buildRuntimeLabTraceCards,
  buildRuntimeLabTranscriptRow,
  buildUserTranscriptRow,
} from './unifiedRoutingChatLab'
import type { RuntimeLabTranscriptRow } from './unifiedRoutingChatLab'

const router = useRouter()
const showIntentSamples = ref(true)
const enabledScenarioIds = ref(AIRLINE_SOP_SCENARIOS.map((scenario) => scenario.id))
const scopeDialogVisible = ref(false)
const inputText = ref('')
const sending = ref(false)
const creatingSession = ref(false)
const traceLoading = ref(false)
const runtimeConfigLoading = ref(false)
const sessionId = ref<number | null>(null)
const runtimeConfig = ref<RuntimeLabConfig | null>(null)
const chatflowTrace = ref<RuntimeLabChatflowTrace | null>(null)
const transcript = ref<RuntimeLabTranscriptRow[]>([])
const tasks = ref<RuntimeLabTask[]>([])
const events = ref<RuntimeLabEvent[]>([])
const latestTurn = ref<RuntimeLabTurn | null>(null)
const messagesEl = ref<HTMLElement>()

const boundScenarios = computed(() => buildRuntimeLabBoundScenarios(runtimeConfig.value))
const boundScenarioIds = computed(() => boundScenarios.value.map((scenario) => scenario.id))
const enabledScenarioSet = computed(() => new Set(enabledScenarioIds.value))
const enabledScenarios = computed(() =>
  boundScenarios.value.filter((scenario) => enabledScenarioSet.value.has(scenario.id)),
)
const triggerSamples = computed(() =>
  enabledScenarios.value.flatMap((scenario) =>
    scenario.triggerUtterances.map((text, index) => ({
      key: `${scenario.id}:trigger:${index}`,
      shortLabel: scenario.shortLabel,
      text,
    })),
  ),
)
const replySamples = computed(() =>
  enabledScenarios.value.flatMap((scenario) =>
    scenario.sampleReplies.map((text, index) => ({
      key: `${scenario.id}:reply:${index}`,
      shortLabel: scenario.shortLabel,
      text,
    })),
  ),
)
const routeScopeLabel = computed(() => `已接通 ${enabledScenarioIds.value.length}/${boundScenarios.value.length || AIRLINE_SOP_SCENARIOS.length} 个意图`)
const lastRouteAction = computed(() => latestTurn.value?.routeDecision.action ?? '待开始')
const configSummary = computed(() => buildRuntimeLabConfigSummary(runtimeConfig.value))
const funnelSummary = computed(() => buildRuntimeLabFunnelSummary(latestTurn.value?.routeDecision))
const chatflowTraceCards = computed(() => buildRuntimeLabTraceCards(chatflowTrace.value))

onMounted(() => {
  void createFreshSession()
  void loadRuntimeLabConfig()
})

function openOrdinaryChat() {
  router.push('/chat')
}

function isScenarioEnabled(scenarioId: string) {
  return enabledScenarioSet.value.has(scenarioId)
}

function setScenarioEnabledFromEvent(scenarioId: string, event: Event) {
  setScenarioEnabled(scenarioId, Boolean((event.target as HTMLInputElement).checked))
}

function setScenarioEnabled(scenarioId: string, enabled: boolean) {
  const next = new Set(enabledScenarioIds.value)
  if (enabled) {
    next.add(scenarioId)
  } else {
    next.delete(scenarioId)
  }
  enabledScenarioIds.value = boundScenarios.value.filter((scenario) => next.has(scenario.id)).map(
    (scenario) => scenario.id,
  )
}

function selectAllScenarios() {
  enabledScenarioIds.value = boundScenarioIds.value
}

function clearScenarios() {
  enabledScenarioIds.value = []
}

async function createFreshSession() {
  creatingSession.value = true
  try {
    const session = await createRuntimeLabSession()
    sessionId.value = session.id
    transcript.value = []
    tasks.value = []
    events.value = []
    chatflowTrace.value = null
    latestTurn.value = null
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建实验会话失败')
  } finally {
    creatingSession.value = false
  }
}

async function loadRuntimeLabConfig() {
  runtimeConfigLoading.value = true
  try {
    runtimeConfig.value = await getRuntimeLabConfig()
    syncEnabledScenarioIdsWithBindings()
  } catch (error) {
    runtimeConfig.value = null
    ElMessage.error(error instanceof Error ? error.message : '加载路由配置失败')
  } finally {
    runtimeConfigLoading.value = false
  }
}

async function sendInput() {
  const content = inputText.value.trim()
  if (!content) return
  inputText.value = ''
  await sendMessage(content)
}

async function sendMessage(content: string) {
  if (sending.value) return
  const currentSessionId = await ensureSession()
  if (!currentSessionId) return

  sending.value = true
  transcript.value.push(buildUserTranscriptRow(uid('user'), content))
  const pendingId = uid('assistant-pending')
  transcript.value.push({
    id: pendingId,
    role: 'assistant',
    content: '',
    pending: true,
  })
  await scrollToBottom()

  try {
    const turn = await postRuntimeLabMessage(currentSessionId, {
      message: content,
      idempotencyKey: uid('front-turn'),
      enabledSopIds: [...enabledScenarioIds.value],
    })
    latestTurn.value = turn
    replacePendingAssistant(pendingId, buildRuntimeLabTranscriptRow(turn))
    await refreshLedger(currentSessionId, turn)
  } catch (error) {
    replacePendingAssistant(pendingId, {
      id: uid('assistant-error'),
      role: 'assistant',
      content: error instanceof Error ? error.message : '发送失败',
      routeAction: 'ERROR',
    })
    ElMessage.error(error instanceof Error ? error.message : '发送失败')
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

async function ensureSession() {
  if (sessionId.value) return sessionId.value
  await createFreshSession()
  return sessionId.value
}

async function refreshLedger(currentSessionId: number, turn: RuntimeLabTurn) {
  tasks.value = [turn.activeTask, ...turn.suspendedTasks].filter(Boolean) as RuntimeLabTask[]
  events.value = turn.events ?? []
  traceLoading.value = true
  try {
    const [taskResult, eventResult, traceResult] = await Promise.all([
      listRuntimeLabTasks(currentSessionId),
      listRuntimeLabEvents(currentSessionId),
      getRuntimeLabChatflowTrace(currentSessionId),
    ])
    tasks.value = taskResult.list
    events.value = eventResult.list
    chatflowTrace.value = traceResult
  } catch {
    // The turn payload is sufficient for the transcript; ledger refresh is best effort.
  } finally {
    traceLoading.value = false
  }
}

function syncEnabledScenarioIdsWithBindings() {
  const ids = boundScenarioIds.value
  if (ids.length === 0) return
  const current = new Set(enabledScenarioIds.value)
  const retained = ids.filter((id) => current.has(id))
  enabledScenarioIds.value = retained.length ? retained : ids
}

function replacePendingAssistant(pendingId: string, row: RuntimeLabTranscriptRow) {
  const index = transcript.value.findIndex((message) => message.id === pendingId)
  if (index >= 0) {
    transcript.value.splice(index, 1, row)
  } else {
    transcript.value.push(row)
  }
}

function openChatflowCanvas(path: string) {
  if (!path) return
  scopeDialogVisible.value = false
  router.push(path)
}

function openChatflowDebug(path: string) {
  if (!path) return
  router.push(path)
}

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}

let localId = 0
function uid(prefix: string) {
  localId += 1
  return `${prefix}-${Date.now()}-${localId}`
}
</script>

<style scoped>
.runtime-lab-layout {
  display: grid;
  grid-template-columns: minmax(16rem, 18rem) minmax(24rem, 1fr) minmax(17rem, 21rem);
  height: 100%;
  overflow: hidden;
  background: var(--color-bg-page);
  color: var(--color-text-primary);
}

.lab-rail,
.lab-inspector {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow-y: auto;
  padding: 1rem;
  border-right: 0.0625rem solid var(--color-border-default);
  background: var(--color-bg-card);
}

.lab-inspector {
  border-right: 0;
  border-left: 0.0625rem solid var(--color-border-default);
}

.lab-panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.875rem;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: 0.5rem;
  background: #fff;
}

.panel-heading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.panel-heading-between {
  justify-content: space-between;
}

.panel-heading-title {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.panel-heading-icon {
  width: 1rem;
  height: 1rem;
  color: var(--color-primary);
}

.samples-toggle {
  flex-shrink: 0;
}

.scope-toolbar {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.system-stack,
.sop-list,
.enabled-scope-list,
.sample-stack,
.task-stack,
.event-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.system-option,
.sop-option,
.sample-chip,
.enabled-scope-chip {
  border: 0.0625rem solid var(--color-border-default);
  border-radius: 0.5rem;
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, background 0.15s;
}

.system-option {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.625rem 0.75rem;
}

.system-option.active,
.sop-option.active,
.enabled-scope-chip {
  border-color: var(--color-primary);
  background: rgba(99, 102, 241, 0.08);
}

.system-title,
.sop-label {
  font-size: 0.8125rem;
  font-weight: 600;
}

.system-meta {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.session-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.runtime-config {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding-top: 0.75rem;
  border-top: 0.0625rem solid var(--color-border-default);
}

.runtime-config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.runtime-config-row strong {
  min-width: 0;
  max-width: 10rem;
  overflow: hidden;
  color: var(--color-text-primary);
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.runtime-binding-details {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.runtime-binding-details summary {
  cursor: pointer;
  color: var(--color-primary);
  font-weight: 700;
}

.runtime-binding-row {
  overflow-wrap: anywhere;
  line-height: 1.5;
}

.session-id,
.muted-line {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.scope-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.scope-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.scope-action {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
}

.enabled-scope-chip {
  display: grid;
  grid-template-columns: 2.25rem 1fr;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.625rem;
}

.enabled-scope-chip:disabled {
  border-color: var(--color-border-default);
  cursor: not-allowed;
  opacity: 0.55;
}

.sop-option {
  display: grid;
  grid-template-columns: 1rem 2.25rem 1fr;
  align-items: center;
  gap: 0.625rem;
  padding: 0.625rem;
}

.sop-checkbox {
  width: 1rem;
  height: 1rem;
  margin: 0;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.sop-short {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2rem;
  border-radius: 0.375rem;
  background: #eef2ff;
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 700;
}

.scope-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.dialog-summary {
  padding-bottom: 0.625rem;
  border-bottom: 0.0625rem solid var(--color-border-default);
}

.sop-dialog-option {
  grid-template-columns: 1rem 2.25rem minmax(0, 1fr) auto;
}

.sop-dialog-option.missing {
  opacity: 0.6;
}

.sop-dialog-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.1875rem;
}

.sop-dialog-main small {
  overflow-wrap: anywhere;
  color: var(--color-text-tertiary);
  font-size: 0.75rem;
  line-height: 1.4;
}

.send-button {
  width: 100%;
}

.sample-chip {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem 0.625rem;
  font-size: 0.75rem;
  line-height: 1.5;
}

.sample-chip:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.sample-chip-tag {
  flex-shrink: 0;
  min-width: 2rem;
  color: var(--color-primary);
  font-weight: 700;
}

.lab-chat {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  background: var(--color-bg-page);
}

.lab-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 1rem 1.25rem;
  border-bottom: 0.0625rem solid var(--color-border-default);
  background: #fff;
}

.lab-chat-header h1 {
  margin: 0;
  font-size: 1rem;
  line-height: 1.4;
}

.lab-header-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
}

.lab-chat-header p {
  margin: 0.1875rem 0 0;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}

.lab-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  height: 100%;
  color: var(--color-text-tertiary);
  font-size: 0.875rem;
}

.empty-icon {
  width: 1.25rem;
  height: 1.25rem;
}

.lab-message {
  display: flex;
  gap: 0.625rem;
  margin-bottom: 0.875rem;
}

.lab-message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
  border-radius: 50%;
  background: #e5e7eb;
  color: var(--color-text-secondary);
  font-size: 0.75rem;
  font-weight: 700;
}

.lab-message.user .message-avatar {
  background: var(--color-primary);
  color: #fff;
}

.message-body {
  max-width: min(42rem, 78%);
  padding: 0.75rem 0.875rem;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: 0.5rem;
  background: #fff;
}

.lab-message.user .message-body {
  background: #eef2ff;
  border-color: rgba(99, 102, 241, 0.24);
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.875rem;
  line-height: 1.6;
}

.typing-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  min-width: 2.5rem;
  min-height: 1.4rem;
}

.typing-indicator span {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 50%;
  background: var(--color-primary);
  animation: runtimeTyping 0.8s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.12s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.24s;
}

.message-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.625rem;
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.resume-prompt,
.resume-box {
  margin-top: 0.625rem;
  padding: 0.5rem 0.625rem;
  border-radius: 0.375rem;
  background: #ecfdf5;
  color: #047857;
  font-size: 0.75rem;
}

.lab-composer {
  display: grid;
  grid-template-columns: 1fr 5.5rem;
  gap: 0.75rem;
  flex-shrink: 0;
  padding: 1rem 1.25rem;
  border-top: 0.0625rem solid var(--color-border-default);
  background: #fff;
}

.decision-list {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  margin: 0;
}

.decision-list div,
.task-row,
.event-row {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
}

.decision-list dt {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.decision-list dd {
  margin: 0;
  max-width: 11rem;
  overflow-wrap: anywhere;
  text-align: right;
  font-size: 0.75rem;
  color: var(--color-text-primary);
}

.task-row,
.event-row {
  padding: 0.5rem 0;
  border-bottom: 0.0625rem solid var(--color-border-default);
  font-size: 0.75rem;
}

.event-seq {
  color: var(--color-text-tertiary);
}

.trace-loading {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  color: var(--color-primary);
  font-size: 0.75rem;
  font-weight: 600;
}

.mini-spinner {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  border: 0.125rem solid rgba(99, 102, 241, 0.2);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: runtimeSpin 0.8s linear infinite;
}

.trace-card {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 0.625rem;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: 0.5rem;
  background: var(--color-bg-page);
}

.trace-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.625rem;
}

.trace-card-head div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.1875rem;
}

.trace-card-head strong {
  overflow-wrap: anywhere;
  font-size: 0.8125rem;
}

.trace-card-head span,
.trace-current {
  color: var(--color-text-tertiary);
  font-size: 0.75rem;
}

.trace-current span {
  color: var(--color-text-primary);
  font-weight: 600;
}

.trace-node-list,
.slot-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.trace-node {
  display: grid;
  grid-template-columns: 1rem minmax(0, 1fr);
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  border: 0.0625rem solid transparent;
  border-radius: 0.375rem;
  background: #fff;
}

.trace-node.current {
  border-color: var(--color-primary);
}

.trace-node-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  background: #e5e7eb;
  color: #047857;
  font-size: 0.75rem;
  font-weight: 700;
}

.trace-node-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.125rem;
}

.trace-node-main span,
.trace-node-main small {
  overflow-wrap: anywhere;
}

.trace-node-main span {
  font-size: 0.75rem;
  font-weight: 600;
}

.trace-node-main small {
  color: var(--color-text-tertiary);
  font-size: 0.6875rem;
}

.slot-row {
  display: flex;
  justify-content: space-between;
  gap: 0.625rem;
  padding-top: 0.375rem;
  border-top: 0.0625rem solid var(--color-border-default);
  font-size: 0.75rem;
}

.slot-row span {
  color: var(--color-text-tertiary);
}

.slot-row strong {
  min-width: 0;
  overflow-wrap: anywhere;
  text-align: right;
  font-weight: 600;
}

@keyframes runtimeTyping {
  0%,
  80%,
  100% {
    transform: translateY(0);
    opacity: 0.45;
  }

  40% {
    transform: translateY(-0.25rem);
    opacity: 1;
  }
}

@keyframes runtimeSpin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 70rem) {
  .runtime-lab-layout {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .lab-rail,
  .lab-inspector {
    border: 0;
  }

  .lab-chat {
    min-height: 38rem;
  }
}
</style>
