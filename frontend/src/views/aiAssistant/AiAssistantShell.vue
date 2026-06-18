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

      <section class="ai-run-list">
        <header>运行记录</header>
        <button
          v-for="run in runs"
          :key="run.id"
          class="ai-run"
          :class="{ active: run.id === runId }"
          type="button"
          data-testid="ai-assistant-run-row"
          :aria-pressed="run.id === runId"
          @click="loadRunInspector(run.id)"
        >
          <span class="ai-run__status" :class="statusClass(run.status)" />
          <span class="ai-run__content">
            <strong>#{{ run.id }} {{ statusLabel(run.status) }}</strong>
            <small>{{ runTitle(run) }}</small>
          </span>
        </button>
      </section>
    </aside>

    <main class="ai-console" data-testid="ai-assistant-conversation-window">
      <header class="ai-console__top">
        <div>
          <h1>{{ sessionTitle }}</h1>
          <p>{{ runStatusLabel }} / Qwen3.5-27B</p>
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
          <a-button
            data-testid="ai-assistant-stream-toggle"
            size="small"
            type="text"
            @click="eventStreamCollapsed = !eventStreamCollapsed"
          >
            <template #icon>
              <DownOutlined v-if="eventStreamCollapsed" />
              <UpOutlined v-else />
            </template>
            {{ eventStreamCollapsed ? '展开回显' : '收起回显' }}
          </a-button>
          <a-tag :color="statusTagColor">{{ runStatusLabel }}</a-tag>
        </div>
      </header>

      <section
        v-if="eventStreamCollapsed"
        class="ai-stream ai-stream--collapsed"
        data-testid="ai-assistant-event-stream"
        data-testid-secondary="ai-assistant-center-column-scroll"
      >
        <button class="ai-stream__restore" type="button" @click="eventStreamCollapsed = false">展开回显</button>
      </section>
      <section
        v-else
        class="ai-stream"
        data-testid="ai-assistant-event-stream"
        data-testid-secondary="ai-assistant-center-column-scroll"
      >
        <div v-if="timeline.length === 0" class="ai-empty">
          <ClockCircleOutlined />
          <span>空闲</span>
        </div>
        <article
          v-for="item in timeline"
          :key="item.id"
          class="ai-event"
          :class="[`tone-${item.tone}`, `kind-${item.kind}`]"
          data-testid="ai-assistant-event-card"
        >
          <div class="ai-event__rail">
            <span class="ai-event__pulse" :class="{ streamPulse: item.tone === 'running' || item.tone === 'waiting' }" />
          </div>
          <div class="ai-event__body">
            <button
              class="ai-event__head"
              type="button"
              data-testid="ai-assistant-event-card-header"
              :aria-expanded="isEventExpanded(item.id)"
              @click="toggleEventCard(item.id)"
            >
              <component :is="eventIcon(item.kind, item.tone)" />
              <span>{{ item.title }}</span>
              <small>#{{ item.sequence }}</small>
              <DownOutlined v-if="!isEventExpanded(item.id)" />
              <UpOutlined v-else />
            </button>
            <div v-if="isEventExpanded(item.id)" class="ai-event__details">
              <p>{{ item.summary }}</p>
              <pre v-if="item.payloadPreview !== '{}'" class="ai-event__payload">{{ item.payloadPreview }}</pre>
              <div v-if="item.kind === 'approval' && item.approvalId" class="ai-event__actions">
                <a-button size="small" type="primary" @click="approve(item.approvalId)">批准</a-button>
                <a-button size="small" danger @click="deny(item.approvalId)">拒绝</a-button>
              </div>
            </div>
          </div>
        </article>
      </section>

      <form class="ai-composer" data-testid="ai-assistant-composer" @submit.prevent="submit">
        <a-textarea
          v-model:value="draft"
          class="ai-composer__input"
          :auto-size="{ minRows: 2, maxRows: 5 }"
          placeholder="输入给 AI 助手的消息"
        />
        <a-button
          class="ai-composer__send"
          data-testid="ai-assistant-send"
          type="primary"
          html-type="submit"
          :loading="sending"
        >
          <template #icon><SendOutlined /></template>
        </a-button>
      </form>
    </main>

    <aside
      class="ai-inspector"
      data-testid="ai-assistant-run-inspector"
      data-testid-secondary="ai-assistant-right-column-scroll"
    >
      <header class="ai-inspector__header">
        <span class="ai-inspector__live" :class="{ statusPulse: sending || runStatus === 'WAITING_APPROVAL' }" />
        <div>
          <strong>{{ runStatusLabel }}</strong>
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
            <small>{{ task.phase }}</small>
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
            <small>{{ statusLabel(toolCall.status) }} / {{ toolCall.durationMs }}ms</small>
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
          <div v-if="approval.status === 'PENDING'" class="ai-approval__actions">
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
          <span>输入</span>
          <strong>{{ inspector?.usage.inputTokens ?? 0 }}</strong>
          <span>输出</span>
          <strong>{{ inspector?.usage.outputTokens ?? 0 }}</strong>
        </div>
      </section>

      <section class="ai-inspector__section" data-testid="ai-assistant-inspector-timeline">
        <header>时间线</header>
        <ol class="ai-mini-timeline">
          <li v-for="event in inspector?.eventTimeline || []" :key="event.id">
            <span>{{ event.sequence }}</span>
            <strong>{{ event.title || event.type }}</strong>
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
  CodeOutlined,
  DeleteOutlined,
  DownOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  SendOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  UpOutlined,
} from '@ant-design/icons-vue'
import { computed, onMounted, ref } from 'vue'

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
  sendAiAssistantMessage,
  type AiAssistantEvent,
  type AiAssistantRun,
  type AiAssistantRunInspector,
  type AiAssistantSession,
} from '@/api/aiAssistant'
import { buildAiAssistantTimeline, type AiAssistantTimelineKind } from './aiAssistantTimeline'

const sessions = ref<AiAssistantSession[]>([])
const runs = ref<AiAssistantRun[]>([])
const sessionId = ref<number | null>(null)
const sessionTitle = ref('Hify AI 助手')
const runId = ref<number | null>(null)
const runStatus = ref('IDLE')
const draft = ref('')
const sending = ref(false)
const events = ref<AiAssistantEvent[]>([])
const inspector = ref<AiAssistantRunInspector | null>(null)
const eventStreamCollapsed = ref(false)
const expandedEventIds = ref<Set<string>>(new Set())

const timeline = computed(() => buildAiAssistantTimeline(events.value))
const pendingApprovals = computed(() => inspector.value?.approvalQueue ?? [])
const approvalRecords = computed(() => inspector.value?.approvalHistory ?? [])
const decidedApprovalRecords = computed(() => approvalRecords.value.filter((approval) => approval.status !== 'PENDING'))
const runStatusLabel = computed(() => (sending.value ? '执行中' : statusLabel(runStatus.value)))
const elapsedLabel = computed(() => `${Math.max(0, Math.round((inspector.value?.usage.elapsedMs ?? 0) / 100) / 10)}s`)
const statusTagColor = computed(() => {
  if (runStatus.value === 'WAITING_APPROVAL') return 'gold'
  if (runStatus.value === 'DENIED') return 'red'
  if (runStatus.value === 'COMPLETED') return 'green'
  return 'blue'
})

onMounted(async () => {
  await loadSessions()
  if (sessions.value.length === 0) {
    await createConversation()
    return
  }
  await selectSession(sessions.value[0].id)
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
  const selected = sessions.value.find((session) => session.id === nextSessionId)
  sessionId.value = nextSessionId
  sessionTitle.value = selected ? sessionDisplayTitle(selected) : 'Hify AI 助手'
  await loadSessionRuns(nextSessionId)
}

async function loadSessionRuns(nextSessionId: number, preferredRunId?: number) {
  runs.value = (await listAiAssistantSessionRuns(nextSessionId)).list
  expandedEventIds.value = new Set()
  const nextRunId = preferredRunId ?? runs.value[0]?.id
  if (!nextRunId) {
    runId.value = null
    runStatus.value = 'IDLE'
    events.value = []
    inspector.value = null
    return
  }
  await loadRunInspector(nextRunId)
}

async function loadRunInspector(nextRunId: number) {
  runId.value = nextRunId
  const [eventList, runInspector] = await Promise.all([
    listAiAssistantRunEvents(nextRunId),
    getAiAssistantRunInspector(nextRunId),
  ])
  events.value = eventList.list
  inspector.value = runInspector
  runStatus.value = runInspector.run.status
}

async function clearCurrentHistory() {
  if (!sessionId.value) return
  await clearAiAssistantSessionHistory(sessionId.value)
  runs.value = []
  events.value = []
  inspector.value = null
  runId.value = null
  runStatus.value = 'IDLE'
  expandedEventIds.value = new Set()
  await loadSessions()
}

async function deleteConversation(targetSessionId: number) {
  const activeSessionId = sessionId.value
  await deleteAiAssistantSession(targetSessionId)
  await loadSessions()
  if (sessions.value.length === 0) return resetConversationAfterDelete()
  if (activeSessionId === targetSessionId || !sessions.value.some((session) => session.id === activeSessionId)) {
    await selectSession(sessions.value[0].id)
  }
}

async function resetConversationAfterDelete() {
  sessionId.value = null
  sessionTitle.value = 'Hify AI 助手'
  runs.value = []
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
    const normalized = message.toLowerCase()
    const asksForUpdate = normalized.includes('update') || /更新|修改|写入|变更/.test(message)
    const result = await sendAiAssistantMessage(sessionId.value, {
      message,
      idempotencyKey: `ui-${Date.now()}`,
      approvalMode: 'smart_approval',
      modelMode: 'live',
      toolName: asksForUpdate ? 'update_customer_profile' : 'echo_context',
      toolInput: asksForUpdate ? { customerId: 'ui-customer', request: message } : undefined,
    })
    draft.value = ''
    runStatus.value = result.status
    await loadSessionRuns(result.sessionId, result.runId)
  } finally {
    sending.value = false
  }
}

async function approve(approvalId: number) {
  await approveAiAssistantApproval(approvalId, { actorId: 'operator-ui' })
  if (runId.value) await loadRunInspector(runId.value)
}

async function deny(approvalId: number) {
  await denyAiAssistantApproval(approvalId, { actorId: 'operator-ui', reason: '界面拒绝' })
  if (runId.value) await loadRunInspector(runId.value)
}

function runTitle(run: AiAssistantRun) {
  const message = typeof run.input?.message === 'string' ? run.input.message : '助手运行'
  return message.length > 42 ? `${message.slice(0, 39)}...` : message
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
    'status-done': status === 'COMPLETED' || status === 'APPROVED',
    'status-waiting': status === 'WAITING_APPROVAL' || status === 'PENDING',
    'status-danger': status === 'DENIED' || status === 'FAILED',
    'status-running': status === 'RUNNING',
  }
}

function eventIcon(kind: AiAssistantTimelineKind, tone: string) {
  if (tone === 'danger') return ExclamationCircleOutlined
  if (tone === 'success') return CheckCircleOutlined
  if (kind === 'tool' || kind === 'tool-output') return ToolOutlined
  return CodeOutlined
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
  gap: 1rem;
  padding: 1rem;
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
.ai-run,
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
.ai-shell :deep(.ant-tag) {
  border: 0;
  box-shadow: none;
}

.ai-shell :deep(.ant-input:focus),
.ai-shell :deep(.ant-input-focused) {
  box-shadow: 0 0 0 0.125rem rgba(79, 70, 229, 0.16);
}

.ai-new-session,
.ai-session__select,
.ai-run {
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
.ai-run-list,
.ai-inspector__section {
  display: flex;
  gap: 0.5rem;
}

.ai-session-list,
.ai-run-list,
.ai-inspector__section {
  flex-direction: column;
}

.ai-run-list {
  margin-top: 1rem;
}

.ai-run-list header,
.ai-inspector__section header {
  color: var(--color-text-tertiary, #8b92a8);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}

.ai-session__select,
.ai-run {
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

.ai-session.active,
.ai-run.active {
  background: var(--color-bg-selected, #eef2ff);
}

.ai-session.active .ai-session__select {
  background: var(--color-bg-selected, #eef2ff);
}

.ai-session__content,
.ai-run__content {
  min-width: 0;
  display: grid;
  gap: 0.125rem;
}

.ai-session__content strong,
.ai-run__content strong,
.ai-task strong,
.ai-inspector-row strong,
.ai-approval strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-session__content small,
.ai-run__content small,
.ai-task small,
.ai-inspector-row small,
.ai-approval small,
.ai-inspector__header small {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-session__dot,
.ai-run__status,
.ai-inspector__live,
.ai-event__pulse,
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
  gap: 1rem;
  padding: 0.875rem 1rem;
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

.ai-stream {
  min-height: 0;
  overflow: auto;
  padding: 1rem;
}

.ai-stream--collapsed {
  display: flex;
  align-items: center;
  justify-content: center;
}

.ai-stream__restore {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2rem;
  padding: 0 0.875rem;
  color: var(--color-primary-600, #4f46e5);
  background: var(--color-bg-selected, #eef2ff);
  border: 0;
  border-radius: var(--radius-md, 0.375rem);
  cursor: pointer;
}

.ai-empty {
  min-height: 18rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-event {
  display: grid;
  grid-template-columns: 1rem minmax(0, 1fr);
  gap: 0.75rem;
  margin-bottom: 0.875rem;
}

.ai-event__rail {
  display: flex;
  justify-content: center;
  padding-top: 0.5rem;
}

.ai-event__body {
  padding: 0.75rem;
  background: var(--color-bg-surface, #ffffff);
  border-radius: var(--radius-lg, 0.5rem);
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

.ai-event__details p {
  margin: 0.5rem 0 0;
  color: var(--color-text-secondary, #4b5268);
}

.ai-event__payload {
  margin: 0.625rem 0 0;
  padding: 0.625rem;
  overflow: auto;
  color: var(--color-text-secondary, #4b5268);
  background: var(--color-bg-page, #f8f9fc);
  border: 0;
  border-radius: var(--radius-md, 0.375rem);
  font-size: 0.75rem;
  line-height: 1.45;
}

.ai-event__actions,
.ai-approval__actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.625rem;
}

.tone-waiting .ai-event__body {
  background: var(--color-warning-50, #fffbeb);
}

.tone-danger .ai-event__body,
.ai-inspector-row.danger {
  background: var(--color-danger-50, #fef2f2);
}

.tone-success .ai-event__body {
  background: var(--color-success-50, #ecfdf5);
}

.ai-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2.75rem;
  gap: 0.625rem;
  padding: 0.875rem 1rem;
  background: var(--color-bg-surface, #ffffff);
}

.ai-composer__input {
  border-radius: 0.5rem;
}

.ai-composer__send {
  height: 100%;
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
  background: var(--color-bg-selected, #eef2ff);
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

.ai-mini-timeline {
  display: grid;
  gap: 0.375rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.ai-mini-timeline li {
  display: grid;
  grid-template-columns: 1.75rem minmax(0, 1fr);
  gap: 0.5rem;
  align-items: center;
  font-size: 0.75rem;
  color: var(--color-text-secondary, #4b5268);
}

.ai-mini-timeline span {
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-mini-timeline strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.streamPulse,
.statusPulse {
  animation: ai-pulse 1.2s ease-in-out infinite;
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
    gap: 0.75rem;
    overflow-x: auto;
    overflow-y: hidden;
  }
}
</style>
