<template>
  <section class="ai-shell" data-testid="ai-assistant-shell">
    <aside class="ai-shell__side" data-testid="ai-assistant-left-column-scroll">
      <div class="ai-shell__brand">
        <ThunderboltOutlined />
        <span>Hify AI 助手</span>
      </div>

      <button
        class="ai-new-session"
        type="button"
        data-testid="ai-assistant-new-session"
        aria-label="新建 AI 助手会话"
        @click="createConversation"
      >
        <PlusOutlined />
        <span>新建会话</span>
      </button>

      <section class="ai-session-list" data-testid="ai-assistant-session-list">
        <article
          v-for="session in sessions"
          :key="session.id"
          class="ai-session"
          :class="{ active: session.id === sessionId }"
          data-testid="ai-assistant-session-row"
        >
          <button class="ai-session__select" type="button" @click="selectSession(session.id)">
            <span class="ai-session__dot" :class="{ statusPulse: session.id === sessionId && sending }" />
            <span class="ai-session__content">
              <strong>{{ sessionDisplayTitle(session) }}</strong>
              <small>{{ statusLabel(session.status) }}</small>
            </span>
          </button>
          <a-button
            class="ai-session__delete"
            data-testid="ai-assistant-delete-session"
            size="small"
            type="text"
            danger
            aria-label="删除会话"
            @click.stop="deleteConversation(session.id)"
          >
            <template #icon><DeleteOutlined /></template>
          </a-button>
        </article>
      </section>
    </aside>

    <main class="ai-console" data-testid="ai-assistant-conversation-window">
      <header class="ai-console__top">
        <div>
          <h1>{{ sessionTitle }}</h1>
        </div>
        <div class="ai-console__actions">
          <a-button
            data-testid="ai-assistant-clear-history"
            size="small"
            type="text"
            :disabled="!sessionId"
            @click="clearCurrentHistory"
          >
            <template #icon><ClearOutlined /></template>
            清空历史上下文
          </a-button>
        </div>
      </header>

      <section
        class="ai-stream"
        data-testid="ai-assistant-event-stream"
        data-testid-secondary="ai-assistant-center-column-scroll"
      >
        <div v-if="runThreads.length === 0" class="ai-empty">
          <ClockCircleOutlined />
          <span>空闲</span>
        </div>
        <template v-else>
          <template v-for="thread in runThreadsForView" :key="thread.run.id">
        <div
          v-if="runThreadUserMessage(thread)"
          class="ai-message ai-message--user"
          data-testid="ai-assistant-user-message"
        >
          <p>{{ runThreadUserMessage(thread) }}</p>
        </div>
        <article class="ai-run-event-group" data-testid="ai-assistant-run-task-card">
          <span class="ai-event__detail-anchor" data-testid="ai-assistant-run-event-group" />
          <button
            class="ai-run-event-group__header"
            type="button"
            data-testid="ai-assistant-run-event-group-header"
            :aria-expanded="isRunEventGroupExpanded(thread.run.id, thread)"
            @click="toggleRunEventGroup(thread.run.id, thread)"
          >
            <span class="ai-run-event-group__status-icon" data-testid="ai-assistant-run-status-icon">
              <LoadingOutlined v-if="isRunThreadRunning(thread)" class="ai-run-event-group__spinner" />
              <CheckCircleOutlined v-else-if="isRunThreadDone(thread)" />
              <ClockCircleOutlined v-else />
            </span>
            <span class="ai-run-event-group__title">
              <strong>{{ runThreadHeaderTitle(thread) }}</strong>
            </span>
            <span class="ai-run-event-group__meta">{{ runThreadMeta(thread) }}</span>
            <DownOutlined v-if="!isRunEventGroupExpanded(thread.run.id, thread)" />
            <UpOutlined v-else />
          </button>

          <section
            v-if="isRunEventGroupExpanded(thread.run.id, thread)"
            class="ai-run-event-line"
            data-testid="ai-assistant-run-event-line"
          >
            <article
              v-for="item in timelineForThreadEcho(thread)"
              :key="item.id"
              class="ai-event"
              :class="[`tone-${eventToneClass(item, thread)}`, `kind-${item.kind}`]"
              data-testid="ai-assistant-event-card"
            >
              <div class="ai-event__rail">
                <span
                  class="ai-event__status-icon"
                  data-testid="ai-assistant-event-status-icon"
                  :class="`tone-${eventToneClass(item, thread)}`"
                >
                  <LoadingOutlined
                    v-if="isEventRunning(item, thread)"
                    class="ai-event__spinner"
                    data-testid="ai-assistant-node-spinner"
                  />
                  <CheckCircleOutlined
                    v-else-if="isEventDone(item, thread)"
                    data-testid="ai-assistant-event-completed-icon"
                  />
                  <component :is="eventStatusIcon(item, thread)" v-else />
                </span>
              </div>
              <div
                class="ai-event__body"
                :data-testid="item.kind === 'model-thought' ? 'ai-assistant-thought-summary' : undefined"
              >
                <button
                  class="ai-event__head"
                  type="button"
                  data-testid="ai-assistant-event-card-header"
                  :aria-expanded="isEventExpanded(item.id)"
                  @click="toggleEventCard(item.id)"
                >
                  <span>{{ item.title }}</span>
                  <small>#{{ item.sequence }}</small>
                  <DownOutlined v-if="!isEventExpanded(item.id)" />
                  <UpOutlined v-else />
                </button>
                <div v-if="item.kind === 'model-output'" class="ai-model-output" data-testid="ai-assistant-model-output">
                  <p>{{ item.summary }}</p>
                </div>
                <div
                  v-if="isEventExpanded(item.id)"
                  class="ai-event__details"
                  data-testid="ai-assistant-event-detail-panel"
                >
                  <dl class="ai-event__detail-grid">
                    <div
                      v-for="row in formatEventDetailRows(item)"
                      :key="row.label"
                      class="ai-event__detail-row"
                      data-testid="ai-assistant-event-detail-row"
                    >
                      <dt>{{ row.label }}</dt>
                      <dd>
                        <pre v-if="row.monospace">{{ row.value }}</pre>
                        <span v-else>{{ row.value }}</span>
                        <span
                          v-if="row.testId === 'ai-assistant-tool-detail-input'"
                          class="ai-event__detail-anchor"
                          data-testid="ai-assistant-tool-detail-input"
                        />
                        <span
                          v-if="row.testId === 'ai-assistant-tool-detail-output'"
                          class="ai-event__detail-anchor"
                          data-testid="ai-assistant-tool-detail-output"
                        />
                      </dd>
                    </div>
                  </dl>
                  <div v-if="shouldShowApprovalActions(item)" class="ai-event__actions">
                    <a-button size="small" type="primary" @click="approveTimelineItem(item)">批准</a-button>
                    <a-button size="small" danger @click="denyTimelineItem(item)">拒绝</a-button>
                  </div>
                </div>
              </div>
            </article>
          </section>
        </article>
        <div
          v-if="runThreadFinalAnswer(thread)"
          class="ai-message ai-message--assistant"
          data-testid="ai-assistant-run-final-answer"
        >
          <p>{{ runThreadFinalAnswer(thread) }}</p>
        </div>
          </template>
        </template>
      </section>

      <form class="ai-composer" data-testid="ai-assistant-composer" @submit.prevent="submit">
        <div class="ai-composer__body" data-testid="ai-assistant-composer-body">
          <a-textarea
            v-model:value="draft"
            class="ai-composer__input"
            :auto-size="{ minRows: 2, maxRows: 5 }"
            placeholder="输入给 AI 助手的消息"
          />
        </div>
        <div class="ai-composer__actions" data-testid="ai-assistant-composer-actions">
          <div class="ai-composer__left-actions">
            <a-button
              class="ai-composer__icon-button"
              data-testid="ai-assistant-add-context"
              type="text"
              aria-label="添加上下文"
            >
              <template #icon><PlusOutlined /></template>
            </a-button>
            <a-dropdown :trigger="['click']">
              <a-button class="ai-composer__permission" data-testid="ai-assistant-permission-mode" type="text">
                <template #icon><SafetyCertificateOutlined /></template>
                {{ permissionModeLabel }}
                <DownOutlined />
              </a-button>
              <template #overlay>
                <a-menu @click="selectPermissionMode">
                  <a-menu-item key="ask_each_time">请求批准</a-menu-item>
                  <a-menu-item key="smart_approval">替我审批</a-menu-item>
                  <a-menu-item key="always_approve">完全访问权限</a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
            <div class="ai-composer__model-config">
              <a-button
                class="ai-composer__icon-button"
                data-testid="ai-assistant-model-config-icon"
                type="text"
                aria-label="模型配置"
                @click="runtimeConfigExpanded = !runtimeConfigExpanded"
              >
                <template #icon><SettingOutlined /></template>
              </a-button>
              <section
                v-if="runtimeConfigExpanded"
                class="ai-composer__model-panel"
                data-testid="ai-assistant-model-config-panel"
              >
                <div class="ai-runtime" data-testid="ai-assistant-runtime-config">
                  <label class="ai-runtime__field">
                    <span>模型</span>
                    <a-select
                      v-model:value="runtimeConfig.modelName"
                      class="ai-runtime__select"
                      :options="modelOptions"
                      data-testid="ai-assistant-model-select"
                    />
                  </label>
                  <label class="ai-runtime__field">
                    <span>接口地址</span>
                    <a-input
                      v-model:value="runtimeConfig.baseUrl"
                      class="ai-runtime__input"
                      placeholder="https://openrouter.ai/api/v1"
                      data-testid="ai-assistant-model-base-url"
                    />
                  </label>
                  <label class="ai-runtime__field">
                    <span>临时密钥</span>
                    <a-input-password
                      v-model:value="runtimeConfig.apiKey"
                      class="ai-runtime__input"
                      placeholder="sk-..."
                      data-testid="ai-assistant-model-api-key"
                    />
                  </label>
                  <label class="ai-runtime__field">
                    <span>温度</span>
                    <a-input-number
                      v-model:value="runtimeConfig.temperature"
                      class="ai-runtime__input"
                      :min="0"
                      :max="2"
                      :step="0.05"
                      :precision="2"
                      data-testid="ai-assistant-model-temperature"
                    />
                  </label>
                  <label class="ai-runtime__field">
                    <span>输出上限</span>
                    <a-input-number
                      v-model:value="runtimeConfig.maxTokens"
                      class="ai-runtime__input"
                      :min="1"
                      :max="32768"
                      :step="128"
                      :precision="0"
                      data-testid="ai-assistant-model-max-tokens"
                    />
                  </label>
                  <div class="ai-runtime__meta">
                    <span>{{ runtimeConfig.baseUrl }}</span>
                    <span>实时事件流：已启用</span>
                  </div>
                </div>
              </section>
            </div>
          </div>
          <a-button
            class="ai-composer__send"
            data-testid="ai-assistant-send"
            type="primary"
            html-type="submit"
            :loading="sending"
            aria-label="发送"
          >
            <template #icon><SendOutlined /></template>
          </a-button>
        </div>
      </form>
    </main>

    <aside
      class="ai-inspector"
      data-testid="ai-assistant-run-inspector"
      data-testid-secondary="ai-assistant-right-column-scroll"
    >
      <header class="ai-inspector__header">
        <ClockCircleOutlined />
        <div>
          <strong>可观测性</strong>
          <small>{{ elapsedLabel }}</small>
        </div>
      </header>

      <section class="ai-inspector__section">
        <header>任务</header>
        <article
          v-for="task in inspector?.activeTasks || []"
          :key="task.id"
          class="ai-task"
          data-testid="ai-assistant-task-row"
        >
          <span class="ai-task__dot" :class="statusClass(task.status)" />
          <div>
            <strong>{{ task.title }}</strong>
            <small>{{ taskMetaLabel(task) }}</small>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section">
        <header>工具调用</header>
        <article
          v-for="toolCall in inspector?.toolCalls || []"
          :key="toolCall.id"
          class="ai-inspector-row"
          data-testid="ai-assistant-tool-call-row"
        >
          <ToolOutlined />
          <div>
            <strong>{{ toolLabel(toolCall.toolName) }}</strong>
            <small>{{ statusLabel(toolCall.status) }} / {{ toolCall.durationMs }} ms</small>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section">
        <header>待审批</header>
        <article
          v-for="approval in pendingApprovals"
          :key="approval.id"
          class="ai-approval"
          data-testid="ai-assistant-approval-row"
        >
          <div>
            <strong>{{ toolLabel(approval.toolName) }}</strong>
            <small>{{ riskLabel(approval.riskLevel) }} / {{ statusLabel(approval.status) }}</small>
          </div>
          <div v-if="isPendingApprovalStatus(approval.status)" class="ai-approval__actions">
            <a-button size="small" type="primary" @click="approve(approval.id)">批准</a-button>
            <a-button size="small" danger @click="deny(approval.id)">拒绝</a-button>
          </div>
        </article>
        <article
          v-for="approval in decidedApprovalRecords"
          :key="`history-${approval.id}`"
          class="ai-approval ai-approval--history"
          data-testid="ai-assistant-approval-history-row"
        >
          <div>
            <strong>{{ toolLabel(approval.toolName) }}</strong>
            <small>{{ riskLabel(approval.riskLevel) }} / {{ statusLabel(approval.status) }}</small>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section">
        <header>最近错误</header>
        <article
          v-for="error in inspector?.recentErrors || []"
          :key="error.id"
          class="ai-inspector-row danger"
          data-testid="ai-assistant-recent-error-row"
        >
          <ExclamationCircleOutlined />
          <div>
            <strong>{{ error.title }}</strong>
            <small>{{ error.summary }}</small>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section">
        <header>用量</header>
        <div class="ai-usage-grid">
          <span>输入 tokens</span>
          <strong>{{ inspector?.usage.inputTokens ?? 0 }}</strong>
          <span>输出 tokens</span>
          <strong>{{ inspector?.usage.outputTokens ?? 0 }}</strong>
          <span>总计 tokens</span>
          <strong>{{ inspector?.usage.totalTokens ?? 0 }}</strong>
          <span>耗时 ms</span>
          <strong>{{ inspector?.usage.elapsedMs ?? 0 }}</strong>
        </div>
      </section>

      <section class="ai-inspector__section" data-testid="ai-assistant-inspector-timeline">
        <header>执行步骤</header>
        <ol class="ai-execution-steps">
          <li v-for="event in inspectorPlanningStepsForView" :key="event.id" data-testid="ai-assistant-execution-step">
            <span class="ai-execution-step__status" :class="statusClass(event.status)">
              <LoadingOutlined v-if="isInspectorEventRunning(event)" class="ai-event__spinner" />
              <CheckCircleOutlined v-else-if="isInspectorEventDone(event)" />
              <ExclamationCircleOutlined v-else-if="event.status === 'FAILED'" />
              <ClockCircleOutlined v-else />
            </span>
            <div>
              <strong>{{ event.title || event.type }}</strong>
              <small>{{ statusLabel(event.status) }}</small>
            </div>
          </li>
        </ol>
      </section>
    </aside>
  </section>
</template>

<script setup lang="ts">
import {
  CheckCircleOutlined,
  ClearOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  DownOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  UpOutlined,
} from '@ant-design/icons-vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  approveAiAssistantApproval,
  clearAiAssistantSessionHistory,
  createAiAssistantSession,
  deleteAiAssistantSession,
  denyAiAssistantApproval,
  getAiAssistantRunInspector,
  listAiAssistantRunEvents,
  listAiAssistantSessionRuns,
  listAiAssistantSessions,
  buildAiAssistantMessagePayload,
  startAiAssistantMessage,
  type AiAssistantEvent,
  type AiAssistantInspectorEvent,
  type AiAssistantApprovalMode,
  type AiAssistantRun,
  type AiAssistantRunInspector,
  type AiAssistantSession,
  type AiAssistantRuntimeConfig,
} from '@/api/aiAssistant'
import { openAiAssistantEventStream, type AiAssistantEventStream } from './aiAssistantEventStream'
import { buildAiAssistantTimeline, type AiAssistantTimelineItem } from './aiAssistantTimeline'

interface AiAssistantRunThread {
  run: AiAssistantRun
  events: AiAssistantEvent[]
  inspector: AiAssistantRunInspector | null
}

interface AiAssistantInspectorTimelineRow extends AiAssistantInspectorEvent {
  groupedCount?: number
}

const AI_ASSISTANT_RUNTIME_CONFIG_STORAGE_KEY = 'hify.ai-assistant.runtime-config'
const DEFAULT_RUNTIME_CONFIG: AiAssistantRuntimeConfig = {
  modelName: 'qwen/qwen3.5-27b',
  baseUrl: 'https://openrouter.ai/api/v1',
  apiKey: '',
  temperature: 0.2,
  maxTokens: 4096,
  streamEnabled: true,
}

const sessions = ref<AiAssistantSession[]>([])
const runs = ref<AiAssistantRun[]>([])
const runThreads = ref<AiAssistantRunThread[]>([])
const sessionId = ref<number | null>(null)
const sessionTitle = ref('Hify AI 助手')
const runId = ref<number | null>(null)
const runStatus = ref('IDLE')
const runtimeConfigExpanded = ref(false)
const runtimeConfig = ref<AiAssistantRuntimeConfig>(loadRuntimeConfig())
const permissionMode = ref<AiAssistantApprovalMode>('smart_approval')
const modelOptions = [
  { label: 'Qwen / qwen3.5-27B', value: 'qwen/qwen3.5-27b' },
  { label: 'Qwen / qwen3.5-14B', value: 'qwen/qwen3.5-14b' },
  { label: 'Qwen / qwen2.5-72B-Instruct', value: 'qwen/qwen2.5-72b-instruct' },
]
const draft = ref('')
const sending = ref(false)
const events = ref<AiAssistantEvent[]>([])
const inspector = ref<AiAssistantRunInspector | null>(null)
const expandedEventIds = ref<Set<string>>(new Set())
const runEventGroupExpanded = ref<Record<number, boolean>>({})
let activeEventStream: AiAssistantEventStream | null = null
let inspectorRefreshTimer: number | null = null

const pendingApprovals = computed(() => inspector.value?.approvalQueue ?? [])
const approvalRecords = computed(() => inspector.value?.approvalHistory ?? [])
const decidedApprovalRecords = computed(() => approvalRecords.value.filter((approval) => approval.status !== 'PENDING'))
const elapsedLabel = computed(() => `${Math.max(0, Math.round((inspector.value?.usage.elapsedMs ?? 0) / 100) / 10)}s`)
const runThreadsForView = computed(() => runThreads.value.slice().sort((left, right) => left.run.id - right.run.id))
const inspectorTimelineForView = computed(() => groupInspectorTimeline(inspector.value?.eventTimeline ?? []))
const inspectorPlanningStepsForView = computed(() => inspectorTimelineForView.value.filter(isModelPlanningInspectorEvent))
const permissionModeLabel = computed(() => permissionModeOptions[permissionMode.value])
const permissionModeOptions: Record<AiAssistantApprovalMode, string> = {
  ask_each_time: '请求批准',
  smart_approval: '替我审批',
  always_approve: '完全访问权限',
}

watch(runtimeConfig, (value) => persistRuntimeConfig(value), { deep: true })

onMounted(async () => {
  await loadSessions()
  if (sessions.value.length === 0) {
    await createConversation()
    return
  }
  await selectSession(sessions.value[0].id)
})

onBeforeUnmount(() => {
  closeActiveEventStream()
  if (inspectorRefreshTimer !== null) window.clearTimeout(inspectorRefreshTimer)
})

async function loadSessions() {
  sessions.value = (await listAiAssistantSessions()).list
}

async function createConversation() {
  const session = await createAiAssistantSession()
  await loadSessions()
  await selectSession(session.id)
}

async function selectSession(nextSessionId: number) {
  closeActiveEventStream()
  const selected = sessions.value.find((session) => session.id === nextSessionId)
  sessionId.value = nextSessionId
  sessionTitle.value = selected ? sessionDisplayTitle(selected) : 'Hify AI 助手'
  await loadSessionRuns(nextSessionId)
}

async function loadSessionRuns(nextSessionId: number, preferredRunId?: number) {
  const sessionRuns = (await listAiAssistantSessionRuns(nextSessionId)).list
  runs.value = sessionRuns
  expandedEventIds.value = new Set()
  runEventGroupExpanded.value = {}
  runThreads.value = await loadRunThreadRecords(sessionRuns)
  const orderedThreads = runThreadsForView.value
  const nextRunId = preferredRunId ?? orderedThreads[orderedThreads.length - 1]?.run.id
  if (!nextRunId) {
    closeActiveEventStream()
    runId.value = null
    runStatus.value = 'IDLE'
    events.value = []
    inspector.value = null
    return
  }
  setActiveRunThread(nextRunId)
}

async function loadRunInspector(nextRunId: number) {
  await refreshRunThread(nextRunId)
}

async function loadRunThreadRecords(sessionRuns: AiAssistantRun[]) {
  const records = await Promise.all(
    sessionRuns.map(async (run) => {
      const [eventList, runInspector] = await Promise.all([
        listAiAssistantRunEvents(run.id),
        getAiAssistantRunInspector(run.id),
      ])
      return {
        run: runInspector.run,
        events: eventList.list,
        inspector: runInspector,
      }
    }),
  )
  return records
}

async function refreshRunThread(nextRunId: number) {
  closeActiveEventStream()
  const [eventList, runInspector] = await Promise.all([
    listAiAssistantRunEvents(nextRunId),
    getAiAssistantRunInspector(nextRunId),
  ])
  upsertRunThread({
    run: runInspector.run,
    events: eventList.list,
    inspector: runInspector,
  })
  setActiveRunThread(nextRunId)
  sending.value = runInspector.run.status === 'RUNNING'
}

function setActiveRunThread(nextRunId: number) {
  const thread = runThreads.value.find((item) => item.run.id === nextRunId)
  if (!thread) return
  runId.value = nextRunId
  events.value = thread.events
  inspector.value = thread.inspector
  runStatus.value = thread.inspector?.run.status ?? thread.run.status
}

async function clearCurrentHistory() {
  if (!sessionId.value) return
  closeActiveEventStream()
  await clearAiAssistantSessionHistory(sessionId.value)
  runs.value = []
  runThreads.value = []
  events.value = []
  inspector.value = null
  runId.value = null
  runStatus.value = 'IDLE'
  expandedEventIds.value = new Set()
  runEventGroupExpanded.value = {}
  await loadSessions()
}

async function deleteConversation(targetSessionId: number) {
  closeActiveEventStream()
  const activeSessionId = sessionId.value
  await deleteAiAssistantSession(targetSessionId)
  await loadSessions()
  if (sessions.value.length === 0) return resetConversationAfterDelete()
  if (activeSessionId === targetSessionId || !sessions.value.some((session) => session.id === activeSessionId)) {
    await selectSession(sessions.value[0].id)
  }
}

async function resetConversationAfterDelete() {
  closeActiveEventStream()
  sessionId.value = null
  sessionTitle.value = 'Hify AI 助手'
  runs.value = []
  runThreads.value = []
  events.value = []
  inspector.value = null
  runId.value = null
  runStatus.value = 'IDLE'
  await createConversation()
}

async function submit() {
  const message = draft.value.trim()
  if (!message) return
  if (!sessionId.value) {
    await createConversation()
  }
  if (!sessionId.value) return
  sending.value = true
  try {
    const result = await startAiAssistantMessage(
      sessionId.value,
      buildAiAssistantMessagePayload(message, runtimeConfig.value, `ui-${Date.now()}`, permissionMode.value),
    )
    draft.value = ''
    events.value = []
    inspector.value = null
    runId.value = result.runId
    runEventGroupExpanded.value = { ...runEventGroupExpanded.value, [result.runId]: true }
    runStatus.value = result.status
    await loadSessions()
    await refreshRuns(result.sessionId, result.runId)
    openRunEventStream(result.runId)
  } finally {
    if (!runId.value || runStatus.value !== 'RUNNING') sending.value = false
  }
}

async function refreshRuns(nextSessionId: number, preferredRunId: number) {
  runs.value = (await listAiAssistantSessionRuns(nextSessionId)).list
  const [eventList, runInspector] = await Promise.all([
    listAiAssistantRunEvents(preferredRunId),
    getAiAssistantRunInspector(preferredRunId),
  ])
  upsertRunThread({
    run: runInspector.run,
    events: eventList.list,
    inspector: runInspector,
  })
  setActiveRunThread(preferredRunId)
  sending.value = runInspector.run.status === 'RUNNING'
}

function openRunEventStream(nextRunId: number) {
  closeActiveEventStream()
  activeEventStream = openAiAssistantEventStream(nextRunId, {
    onEvent: (event) => {
      mergeEvent(event)
      runStatus.value = event.status === 'FAILED' ? 'FAILED' : runStatus.value
      scheduleInspectorRefresh(nextRunId)
      if (isTerminalEvent(event)) {
        sending.value = false
        if (event.type !== 'approval.required') collapseRunEventGroup(event.runId)
        closeActiveEventStream()
      }
    },
  })
}

function mergeEvent(event: AiAssistantEvent) {
  const index = events.value.findIndex((item) => item.id === event.id)
  if (index >= 0) {
    events.value = events.value.map((item) => (item.id === event.id ? event : item))
  } else {
    events.value = [...events.value, event].sort((left, right) => left.sequence - right.sequence)
  }
  mergeEventIntoRunThread(event)
}

function scheduleInspectorRefresh(nextRunId: number) {
  if (inspectorRefreshTimer !== null) return
  inspectorRefreshTimer = window.setTimeout(async () => {
    inspectorRefreshTimer = null
    const runInspector = await getAiAssistantRunInspector(nextRunId)
    inspector.value = runInspector
    runStatus.value = runInspector.run.status
    sending.value = runInspector.run.status === 'RUNNING'
    upsertRunThread({
      run: runInspector.run,
      events: events.value,
      inspector: runInspector,
    })
  }, 350)
}

function upsertRunThread(thread: AiAssistantRunThread) {
  const index = runThreads.value.findIndex((item) => item.run.id === thread.run.id)
  if (index >= 0) {
    runThreads.value = runThreads.value.map((item) => (item.run.id === thread.run.id ? thread : item))
    return
  }
  runThreads.value = [...runThreads.value, thread]
}

function mergeEventIntoRunThread(event: AiAssistantEvent) {
  const currentThread = runThreads.value.find((thread) => thread.run.id === event.runId)
  const nextRun = currentThread?.run ?? {
    id: event.runId,
    sessionId: event.sessionId,
    status: runStatusFromEvent(event, runStatus.value),
    input: { message: draft.value },
    result: {},
  }
  const nextEvents = [...(currentThread?.events ?? [])]
  const index = nextEvents.findIndex((item) => item.id === event.id)
  if (index >= 0) nextEvents[index] = event
  else nextEvents.push(event)
  upsertRunThread({
    run: { ...nextRun, status: runStatusFromEvent(event, nextRun.status) },
    events: nextEvents.sort((left, right) => left.sequence - right.sequence),
    inspector: currentThread?.inspector ?? null,
  })
}

function runStatusFromEvent(event: AiAssistantEvent, fallback: string) {
  if (event.type === 'run.completed') return 'COMPLETED'
  if (event.type === 'run.failed') return 'FAILED'
  if (event.type === 'approval.required') return 'WAITING_APPROVAL'
  if (event.type === 'run.started') return 'RUNNING'
  return fallback
}

function closeActiveEventStream() {
  activeEventStream?.close()
  activeEventStream = null
}

function isTerminalEvent(event: AiAssistantEvent) {
  return ['run.completed', 'run.failed', 'approval.required', 'sandbox.denied'].includes(event.type)
}

async function approve(approvalId: number) {
  await approveAiAssistantApproval(approvalId, { actorId: 'operator-ui' })
  if (runId.value) await loadRunInspector(runId.value)
}

async function deny(approvalId: number) {
  await denyAiAssistantApproval(approvalId, { actorId: 'operator-ui', reason: '界面拒绝' })
  if (runId.value) await loadRunInspector(runId.value)
}

function loadRuntimeConfig(): AiAssistantRuntimeConfig {
  if (typeof window === 'undefined') return { ...DEFAULT_RUNTIME_CONFIG }
  try {
    const stored = window.sessionStorage.getItem(AI_ASSISTANT_RUNTIME_CONFIG_STORAGE_KEY)
    if (!stored) return { ...DEFAULT_RUNTIME_CONFIG }
    return { ...DEFAULT_RUNTIME_CONFIG, ...JSON.parse(stored) }
  } catch {
    return { ...DEFAULT_RUNTIME_CONFIG }
  }
}

function persistRuntimeConfig(value: AiAssistantRuntimeConfig) {
  if (typeof window === 'undefined') return
  window.sessionStorage.setItem(AI_ASSISTANT_RUNTIME_CONFIG_STORAGE_KEY, JSON.stringify(value))
}

function selectPermissionMode(event: { key: string | number }) {
  const key = String(event.key)
  if (isApprovalMode(key)) permissionMode.value = key
}

function isApprovalMode(value: string): value is AiAssistantApprovalMode {
  return value === 'ask_each_time' || value === 'smart_approval' || value === 'always_approve'
}

function timelineForThread(thread: AiAssistantRunThread) {
  return buildAiAssistantTimeline(thread.events)
}

function runThreadUserMessage(thread: AiAssistantRunThread) {
  const message = thread.run.input?.message
  return typeof message === 'string' ? message.trim() : ''
}

function timelineForThreadEcho(thread: AiAssistantRunThread) {
  return timelineForThread(thread).filter((item) => !isFinalAnswerItem(item))
}

function isFinalAnswerItem(item: AiAssistantTimelineItem) {
  return item.kind === 'model-output' && (item.phase === 'final_answer' || item.source === 'harness_final_answer')
}

function runThreadFinalAnswer(thread: AiAssistantRunThread) {
  const status = thread.inspector?.run.status ?? thread.run.status
  if (!['COMPLETED', 'APPROVED'].includes(status)) return ''
  const resultAnswer = finalAnswerFromRun(thread.inspector?.run ?? thread.run)
  if (resultAnswer) return resultAnswer
  return timelineForThread(thread)
    .filter(isFinalAnswerItem)
    .map((item) => item.summary.trim())
    .filter(Boolean)
    .join('\n\n')
}

function finalAnswerFromRun(run: AiAssistantRun) {
  const answer = run.result?.finalAnswer
  return typeof answer === 'string' ? answer.trim() : ''
}

function runThreadHeaderTitle(thread: AiAssistantRunThread) {
  const status = thread.inspector?.run.status ?? thread.run.status
  if (status === 'RUNNING') return '执行中'
  if (status === 'WAITING_APPROVAL' || status === 'PENDING') return '等待审批'
  if (status === 'FAILED') return '处理失败'
  if (status === 'DENIED') return '已拒绝'
  if (status === 'COMPLETED' || status === 'APPROVED') return '已处理'
  return statusLabel(status)
}

function runThreadMeta(thread: AiAssistantRunThread) {
  const timeline = timelineForThreadEcho(thread)
  const toolCount = thread.inspector?.toolCalls.length ?? 0
  return `${timeline.length} 条事件 / ${toolCount} 次工具`
}

function taskMetaLabel(task: { phase: string; currentTool?: string | null }) {
  const currentTool = task.currentTool ? ` / ${toolLabel(task.currentTool)}` : ''
  const eventCount = inspectorTimelineForView.value.length
  return `${task.phase}${currentTool} / ${eventCount} 条事件`
}

function isModelPlanningInspectorEvent(event: AiAssistantInspectorTimelineRow) {
  return [
    'model.stream_chunk',
    'model.thought_summary',
    'model.tool_call_decision',
    'model.file_intent',
    'model.skill_intent',
  ].includes(event.type)
}

function isInspectorEventRunning(event: AiAssistantInspectorTimelineRow) {
  return event.status === 'RUNNING' || event.status === 'PENDING' || event.status === 'STREAMING'
}

function isInspectorEventDone(event: AiAssistantInspectorTimelineRow) {
  return !isInspectorEventRunning(event) && event.status !== 'FAILED' && event.status !== 'DENIED'
}

function groupInspectorTimeline(events: AiAssistantInspectorEvent[]): AiAssistantInspectorTimelineRow[] {
  const rows: AiAssistantInspectorTimelineRow[] = []
  let streamGroup: AiAssistantInspectorEvent[] = []

  const flushStreamGroup = () => {
    if (streamGroup.length === 0) return
    const first = streamGroup[0]
    const last = streamGroup[streamGroup.length - 1]
    rows.push({
      ...last,
      id: first.id,
      sequence: first.sequence,
      title: '模型输出',
      summary: `已聚合 ${streamGroup.length} 段流式输出`,
      groupedCount: streamGroup.length,
    })
    streamGroup = []
  }

  for (const event of events) {
    if (event.type === 'model.stream_chunk') {
      streamGroup.push(event)
      continue
    }
    flushStreamGroup()
    rows.push(event)
  }
  flushStreamGroup()
  return rows
}

function isRunThreadRunning(thread: AiAssistantRunThread) {
  return (thread.inspector?.run.status ?? thread.run.status) === 'RUNNING'
}

function isRunThreadDone(thread: AiAssistantRunThread) {
  const status = thread.inspector?.run.status ?? thread.run.status
  return status === 'COMPLETED' || status === 'APPROVED'
}

function sessionDisplayTitle(session: AiAssistantSession) {
  const title = session.title?.trim()
  if (!title || title === 'AI Assistant' || title === 'Hify AI 助手') return `会话 #${session.id}`
  return title
}

function statusLabel(status: string) {
  return (
    {
      IDLE: '空闲',
      ACTIVE: '活跃',
      OK: '已完成',
      RUNNING: '执行中',
      COMPLETED: '已完成',
      WAITING_APPROVAL: '等待审批',
      PENDING: '待处理',
      APPROVED: '已批准',
      DENIED: '已拒绝',
      FAILED: '失败',
      BLOCKED: '已阻断',
      NOT_FOUND: '未找到',
    }[status] ?? status
  )
}

function toolLabel(toolName: string) {
  return (
    {
      echo_context: '上下文回显',
      update_customer_profile: '客户资料变更',
      run_shell: 'Shell 执行',
      customer_assistant_subagent_bridge: '客服助手子任务桥接',
      read_workspace_file: '读取工作区文件',
      write_workspace_file: '写入工作区文件',
      invoke_skill: '技能意图',
      search_knowledge_base: '知识库检索',
    }[toolName] ?? toolName
  )
}

function riskLabel(riskLevel: string) {
  return (
    {
      READ: '只读',
      LOW_WRITE: '低风险写入',
      BUSINESS_WRITE: '业务写入',
      DESTRUCTIVE: '破坏性操作',
      EXTERNAL_SIDE_EFFECT: '外部副作用',
    }[riskLevel] ?? riskLevel
  )
}

function statusClass(status: string) {
  return {
    'status-done': status === 'COMPLETED' || status === 'APPROVED' || status === 'OK',
    'status-waiting': status === 'WAITING_APPROVAL' || status === 'PENDING',
    'status-danger': status === 'DENIED' || status === 'FAILED',
    'status-running': status === 'RUNNING',
  }
}

function eventStatusIcon(item: AiAssistantTimelineItem, _thread: AiAssistantRunThread) {
  const { kind, tone } = item
  if (tone === 'danger') return ExclamationCircleOutlined
  if (kind === 'tool' || kind === 'tool-output') return ToolOutlined
  return ClockCircleOutlined
}

function toggleEventCard(itemId: string) {
  const next = new Set(expandedEventIds.value)
  if (next.has(itemId)) next.delete(itemId)
  else next.add(itemId)
  expandedEventIds.value = next
}

function isEventExpanded(itemId: string) {
  return expandedEventIds.value.has(itemId)
}

function toggleRunEventGroup(targetRunId: number, thread?: AiAssistantRunThread) {
  const current = isRunEventGroupExpanded(targetRunId, thread)
  runEventGroupExpanded.value = { ...runEventGroupExpanded.value, [targetRunId]: !current }
}

function collapseRunEventGroup(targetRunId: number) {
  runEventGroupExpanded.value = { ...runEventGroupExpanded.value, [targetRunId]: false }
}

function isRunEventGroupExpanded(targetRunId: number, thread?: AiAssistantRunThread) {
  const explicit = runEventGroupExpanded.value[targetRunId]
  return typeof explicit === 'boolean' ? explicit : runThreadDefaultExpanded(thread)
}

function runThreadDefaultExpanded(thread?: AiAssistantRunThread) {
  return thread ? isRunThreadRunning(thread) : runStatus.value === 'RUNNING'
}

function formatEventDetailRows(item: AiAssistantTimelineItem) {
  return item.details
}

function shouldShowApprovalActions(item: AiAssistantTimelineItem) {
  return item.kind === 'approval' && item.approvalId && item.tone === 'waiting'
}

function isPendingApprovalStatus(status: string) {
  return status === 'PENDING' || status === 'WAITING_APPROVAL'
}

function approveTimelineItem(item: AiAssistantTimelineItem) {
  if (item.approvalId) return approve(item.approvalId)
}

function denyTimelineItem(item: AiAssistantTimelineItem) {
  if (item.approvalId) return deny(item.approvalId)
}

function isEventRunning(item: AiAssistantTimelineItem, thread: AiAssistantRunThread) {
  if (!isRunThreadRunning(thread)) return false
  const timeline = timelineForThreadEcho(thread)
  return item.id === timeline[timeline.length - 1]?.id && item.tone === 'running'
}

function isEventDone(item: AiAssistantTimelineItem, thread: AiAssistantRunThread) {
  return !isEventRunning(item, thread) && item.tone !== 'waiting' && item.tone !== 'danger'
}

function eventToneClass(item: AiAssistantTimelineItem, thread: AiAssistantRunThread) {
  if (isEventRunning(item, thread)) return 'running'
  if (isEventDone(item, thread)) return 'success'
  return item.tone
}
</script>

<style scoped>
.ai-shell {
  height: calc(100vh - var(--header-height, 3.5rem) - 3rem);
  max-height: calc(100vh - var(--header-height, 3.5rem) - 3rem);
  box-sizing: border-box;
  min-height: 0;
  display: grid;
  grid-template-columns: 15rem minmax(0, 1fr) 18rem;
  grid-template-rows: minmax(0, 1fr);
  gap: 0;
  padding: 0;
  background: var(--color-bg-page, #f8f9fc);
  color: var(--color-text-primary, #0f1117);
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
  border-radius: var(--radius-lg, 0.5rem);
  overflow: hidden;
}

.ai-shell__side,
.ai-inspector,
.ai-console {
  min-width: 0;
  min-height: 0;
  background: var(--color-bg-surface, #ffffff);
  box-shadow: none;
}

.ai-shell__side,
.ai-inspector {
  padding: 0.75rem;
  overflow: auto;
}

.ai-shell__brand,
.ai-new-session,
.ai-session,
.ai-session__select,
.ai-console__top,
.ai-console__actions,
.ai-event__head,
.ai-inspector__header,
.ai-inspector-row,
.ai-task,
.ai-approval {
  display: flex;
  align-items: center;
}

.ai-shell__brand {
  gap: 0.5rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
}

.ai-shell :deep(.ant-btn),
.ai-shell :deep(.ant-input),
.ai-shell :deep(.ant-input-number),
.ai-shell :deep(.ant-select),
.ai-shell :deep(.ant-select-selector),
.ai-shell :deep(.ant-tag) {
  border: 0;
  box-shadow: none;
}

.ai-shell :deep(.ant-select-selector),
.ai-shell :deep(.ant-input),
.ai-shell :deep(.ant-input-number) {
  background: var(--color-bg-page, #f8f9fc);
  border-radius: var(--radius-md, 0.375rem);
}

.ai-shell :deep(.ant-input-number-input-wrap),
.ai-shell :deep(.ant-select-selection-item),
.ai-shell :deep(.ant-select-selection-placeholder) {
  border: 0;
  box-shadow: none;
}

.ai-shell :deep(.ant-input:focus),
.ai-shell :deep(.ant-input-focused) {
  box-shadow: 0 0 0 0.125rem rgba(79, 70, 229, 0.16);
}

.ai-new-session,
.ai-session__select {
  width: 100%;
  gap: 0.5rem;
  color: inherit;
  text-align: left;
  border: 0;
  border-radius: var(--radius-md, 0.375rem);
}

.ai-new-session {
  justify-content: center;
  padding: 0.5625rem;
  margin-bottom: 0.75rem;
  background: var(--color-bg-selected, #eef2ff);
  color: var(--color-primary-600, #4f46e5);
}

.ai-session-list,
.ai-inspector__section {
  display: flex;
  gap: 0.5rem;
}

.ai-session-list,
.ai-inspector__section {
  flex-direction: column;
}

.ai-inspector__section header {
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}

.ai-session__select {
  padding: 0.625rem;
  background: var(--color-bg-surface, #ffffff);
}

.ai-session {
  min-width: 0;
  gap: 0.25rem;
  border-radius: var(--radius-md, 0.375rem);
  background: var(--color-bg-surface, #ffffff);
}

.ai-session__select {
  min-width: 0;
  flex: 1;
  padding-right: 0.25rem;
  border: 0;
  border-radius: calc(var(--radius-md, 0.375rem) - 0.0625rem);
}

.ai-session__delete {
  flex: 0 0 auto;
  margin-right: 0.25rem;
}

.ai-session.active {
  background: var(--color-bg-selected, #eef2ff);
}

.ai-session.active .ai-session__select {
  background: var(--color-bg-selected, #eef2ff);
}

.ai-session__content {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.ai-session__content strong,
.ai-task strong,
.ai-inspector-row strong,
.ai-approval strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-session__content small,
.ai-task small,
.ai-inspector-row small,
.ai-approval small,
.ai-inspector__header small {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-session__dot,
.ai-inspector__live,
.ai-task__dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--color-text-tertiary, #8b92a8);
  display: inline-block;
  flex: 0 0 auto;
}

.status-done,
.ai-session__dot {
  background: var(--color-success-500, #10b981);
}

.status-waiting {
  background: var(--color-warning-500, #f59e0b);
}

.status-danger {
  background: var(--color-danger-500, #ef4444);
}

.status-running {
  background: var(--color-info-500, #3b82f6);
}

.ai-console {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
}

.ai-console__top {
  justify-content: space-between;
  gap: 0.625rem;
  padding: 0.625rem;
}

.ai-console__actions {
  flex: 0 0 auto;
}

.ai-console__top h1 {
  margin: 0;
  font-size: 1rem;
}

.ai-console__top p {
  margin: 0.25rem 0 0;
  color: var(--color-text-secondary, #4b5268);
}

.ai-runtime {
  display: grid;
  gap: 0.625rem;
  padding: 0.75rem;
}

.ai-runtime__field {
  min-width: 0;
  display: grid;
  gap: 0.25rem;
}

.ai-runtime__field span {
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
  font-weight: 600;
}

.ai-runtime__select,
.ai-runtime__input {
  width: 100%;
}

.ai-runtime__meta {
  min-width: 0;
  display: grid;
  gap: 0.25rem;
  color: var(--color-text-secondary, #4b5268);
  font-size: 0.75rem;
}

.ai-runtime__meta span:last-child {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-stream {
  min-height: 0;
  overflow: auto;
  padding: 0.625rem;
}

.ai-empty {
  min-height: 18rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-run-event-group {
  display: grid;
  gap: 0.625rem;
}

.ai-message {
  display: grid;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: 0;
}

.ai-message p {
  margin: 0;
  line-height: 1.6;
  white-space: pre-wrap;
}

.ai-message--user {
  justify-items: end;
  color: var(--color-text-primary, #0f1117);
}

.ai-message--assistant {
  color: var(--color-text-primary, #0f1117);
}

.ai-message--user p,
.ai-message--assistant p {
  max-width: min(42rem, 100%);
}

.ai-run-event-group__header {
  width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  gap: 0.625rem;
  align-items: center;
  padding: 0.75rem;
  color: inherit;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: var(--radius-lg, 0.5rem);
  cursor: pointer;
}

.ai-run-event-group__status-icon {
  width: 1rem;
  height: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-success-500, #10b981);
  flex: 0 0 auto;
}

.ai-run-event-group__spinner,
.ai-event__spinner {
  color: var(--color-primary-600, #4f46e5);
  animation: ai-spin 0.9s linear infinite;
}

.ai-run-event-group__title {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.ai-run-event-group__title small,
.ai-run-event-group__meta {
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
}

.ai-run-event-group__title strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-run-event-group__meta {
  white-space: nowrap;
}

.ai-run-event-line {
  display: grid;
  gap: 0;
  padding: 0.25rem 0 0.125rem;
}

.ai-event {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr);
  gap: 0.75rem;
  margin: 0;
}

.ai-event:not(:last-child) {
  padding-bottom: 0.875rem;
}

.ai-event__rail {
  position: relative;
  display: flex;
  justify-content: center;
  padding-top: 0.375rem;
}

.ai-event:not(:last-child) .ai-event__rail::after {
  content: '';
  position: absolute;
  top: 1.375rem;
  bottom: -0.875rem;
  width: 0.0625rem;
  background: var(--color-border-default, #e3e6ef);
}

.ai-event__status-icon,
.ai-event__spinner {
  position: relative;
  z-index: 1;
  font-size: 0.875rem;
}

.ai-event__status-icon {
  width: 1rem;
  height: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-surface, #ffffff);
  color: var(--color-border-strong, #c7ccd8);
}

.ai-event__body {
  display: grid;
  gap: 0.5rem;
  padding: 0 0 0.625rem;
  background: transparent;
  border-radius: 0;
}

.ai-model-output {
  display: grid;
  gap: 0.25rem;
}

.ai-model-output p {
  margin: 0;
  color: var(--color-text-primary, #0f1117);
  line-height: 1.6;
  white-space: pre-wrap;
}

.ai-event__summary {
  margin: 0;
  color: var(--color-text-secondary, #4b5268);
  line-height: 1.55;
}

.ai-event__head {
  width: 100%;
  gap: 0.5rem;
  font-weight: 700;
  color: inherit;
  background: transparent;
  border: 0;
  cursor: pointer;
  text-align: left;
}

.ai-event__head small {
  margin-left: auto;
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-event__details {
  display: grid;
  gap: 0.5rem;
}

.ai-event__detail-grid {
  display: grid;
  gap: 0.5rem;
  margin: 0;
}

.ai-event__detail-row {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: 0.625rem;
  padding: 0.625rem;
  background: var(--color-bg-page, #f8f9fc);
  border-radius: var(--radius-md, 0.375rem);
}

.ai-event__detail-anchor {
  position: absolute;
  width: 0;
  height: 0;
  overflow: hidden;
}

.ai-event__detail-row dt {
  color: var(--color-text-tertiary, #8b92a8);
  font-weight: 700;
}

.ai-event__detail-row dd {
  min-width: 0;
  margin: 0;
  color: var(--color-text-secondary, #4b5268);
}

.ai-event__detail-row pre {
  max-height: 14rem;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  font-size: 0.75rem;
  line-height: 1.45;
}

.ai-event__actions,
.ai-approval__actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.625rem;
}

.tone-danger,
.ai-inspector-row.danger {
  color: var(--color-danger-600, #dc2626);
}

.ai-composer {
  display: grid;
  grid-template-rows: auto auto;
  gap: 0.375rem;
  padding: 0.625rem 0.625rem;
  background: var(--color-bg-surface, #ffffff);
}

.ai-composer__body {
  min-width: 0;
}

.ai-composer__input {
  border-radius: 0.5rem;
}

.ai-composer__actions,
.ai-composer__left-actions {
  display: flex;
  align-items: center;
}

.ai-composer__actions {
  justify-content: space-between;
  gap: 0.625rem;
}

.ai-composer__left-actions {
  min-width: 0;
  gap: 0.25rem;
}

.ai-composer__model-config {
  position: relative;
  display: inline-flex;
}

.ai-composer__model-panel {
  position: absolute;
  right: 0;
  bottom: calc(100% + 0.5rem);
  z-index: 20;
  width: min(26rem, calc(100vw - 3rem));
  background: var(--color-bg-surface, #ffffff);
  border-radius: var(--radius-lg, 0.5rem);
  box-shadow: var(--shadow-lg, 0 1rem 2rem rgba(15, 17, 23, 0.14));
}

.ai-composer__icon-button,
.ai-composer__permission {
  min-width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
}

.ai-composer__permission {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  max-width: 12rem;
  color: var(--color-text-secondary, #4b5268);
}

.ai-composer__send {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.5rem;
}

.ai-inspector {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  overflow: auto;
}

.ai-inspector__header {
  gap: 0.75rem;
  padding: 0.625rem;
  background: transparent;
  border-radius: var(--radius-md, 0.375rem);
}

.ai-task,
.ai-inspector-row,
.ai-approval {
  gap: 0.625rem;
  padding: 0.625rem;
  background: var(--color-bg-surface, #ffffff);
  border: 0;
  border-radius: var(--radius-md, 0.375rem);
}

.ai-task > div,
.ai-inspector-row > div,
.ai-approval > div {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.ai-approval {
  align-items: flex-start;
  flex-direction: column;
}

.ai-usage-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.375rem 0.75rem;
  padding: 0.625rem;
  background: var(--color-bg-page, #f8f9fc);
  border: 0;
  border-radius: var(--radius-md, 0.375rem);
}

.ai-usage-grid span {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-execution-steps {
  display: grid;
  gap: 0.375rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.ai-execution-steps li {
  display: grid;
  grid-template-columns: 1.75rem minmax(0, 1fr);
  gap: 0.5rem;
  align-items: start;
  font-size: 0.75rem;
  color: var(--color-text-secondary, #4b5268);
}

.ai-execution-step__status {
  width: 1rem;
  height: 1rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.ai-execution-steps span {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-execution-steps div {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.ai-execution-steps strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-execution-steps small {
  color: var(--color-text-tertiary, #8b92a8);
}

.statusPulse {
  animation: ai-pulse 1.2s ease-in-out infinite;
}

@keyframes ai-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes ai-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.35);
  }
  100% {
    box-shadow: 0 0 0 0.625rem rgba(99, 102, 241, 0);
  }
}

@media (max-width: 70rem) {
  .ai-shell {
    grid-template-columns: 12rem minmax(22rem, 1fr) 16rem;
    gap: 0;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .ai-composer__model-panel {
    right: auto;
    left: 0;
    width: min(22rem, calc(100vw - 2rem));
  }
}
</style>
