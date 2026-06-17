<template>
  <section class="ai-shell" data-testid="ai-assistant-shell">
    <aside class="ai-shell__side">
      <div class="ai-shell__brand">
        <ThunderboltOutlined />
        <span>AI Assistant</span>
      </div>

      <button class="ai-new-session" type="button" @click="createConversation">
        <PlusOutlined />
        <span>New Run</span>
      </button>

      <section class="ai-session-list" data-testid="ai-assistant-session-list">
        <button
          v-for="session in sessions"
          :key="session.id"
          class="ai-session"
          :class="{ active: session.id === sessionId }"
          type="button"
          data-testid="ai-assistant-session-row"
          @click="selectSession(session.id)"
        >
          <span class="ai-session__dot" :class="{ statusPulse: session.id === sessionId && sending }" />
          <span class="ai-session__content">
            <strong>{{ session.title || 'AI Assistant' }}</strong>
            <small>{{ session.status }}</small>
          </span>
        </button>
      </section>

      <section class="ai-run-list">
        <header>Runs</header>
        <button
          v-for="run in runs"
          :key="run.id"
          class="ai-run"
          :class="{ active: run.id === runId }"
          type="button"
          @click="loadRunInspector(run.id)"
        >
          <span class="ai-run__status" :class="statusClass(run.status)" />
          <span class="ai-run__content">
            <strong>#{{ run.id }} {{ run.status }}</strong>
            <small>{{ runTitle(run) }}</small>
          </span>
        </button>
      </section>
    </aside>

    <main class="ai-console" data-testid="ai-assistant-conversation-window">
      <header class="ai-console__top">
        <div>
          <h1>{{ sessionTitle }}</h1>
          <p>{{ runStatusLabel }}</p>
        </div>
        <a-tag :color="statusTagColor">{{ runStatusLabel }}</a-tag>
      </header>

      <section class="ai-stream" data-testid="ai-assistant-event-stream">
        <div v-if="timeline.length === 0" class="ai-empty">
          <ClockCircleOutlined />
          <span>Ready</span>
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
            <div class="ai-event__head">
              <component :is="eventIcon(item.kind, item.tone)" />
              <span>{{ item.title }}</span>
              <small>#{{ item.sequence }}</small>
            </div>
            <p>{{ item.summary }}</p>
            <pre v-if="item.payloadPreview !== '{}'" class="ai-event__payload">{{ item.payloadPreview }}</pre>
            <div v-if="item.kind === 'approval' && item.approvalId" class="ai-event__actions">
              <a-button size="small" type="primary" @click="approve(item.approvalId)">Approve</a-button>
              <a-button size="small" danger @click="deny(item.approvalId)">Deny</a-button>
            </div>
          </div>
        </article>
      </section>

      <form class="ai-composer" data-testid="ai-assistant-composer" @submit.prevent="submit">
        <a-textarea
          v-model:value="draft"
          class="ai-composer__input"
          :auto-size="{ minRows: 2, maxRows: 5 }"
          placeholder="Message AI Assistant"
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

    <aside class="ai-inspector" data-testid="ai-assistant-run-inspector">
      <header class="ai-inspector__header">
        <span class="ai-inspector__live" :class="{ statusPulse: sending || runStatus === 'WAITING_APPROVAL' }" />
        <div>
          <strong>{{ runStatusLabel }}</strong>
          <small>{{ elapsedLabel }}</small>
        </div>
      </header>

      <section class="ai-inspector__section">
        <header>Tasks</header>
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
        <header>Tool Calls</header>
        <article
          v-for="toolCall in inspector?.toolCalls || []"
          :key="toolCall.id"
          class="ai-inspector-row"
          data-testid="ai-assistant-tool-call-row"
        >
          <ToolOutlined />
          <div>
            <strong>{{ toolCall.toolName }}</strong>
            <small>{{ toolCall.status }} / {{ toolCall.durationMs }}ms</small>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section">
        <header>Approvals</header>
        <article
          v-for="approval in inspector?.approvalQueue || []"
          :key="approval.id"
          class="ai-approval"
          data-testid="ai-assistant-approval-row"
        >
          <div>
            <strong>{{ approval.toolName }}</strong>
            <small>{{ approval.riskLevel }} / {{ approval.status }}</small>
          </div>
          <div v-if="approval.status === 'PENDING'" class="ai-approval__actions">
            <a-button size="small" type="primary" @click="approve(approval.id)">Approve</a-button>
            <a-button size="small" danger @click="deny(approval.id)">Deny</a-button>
          </div>
        </article>
      </section>

      <section class="ai-inspector__section">
        <header>Recent Errors</header>
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
        <header>Usage</header>
        <div class="ai-usage-grid">
          <span>Input</span>
          <strong>{{ inspector?.usage.inputTokens ?? 0 }}</strong>
          <span>Output</span>
          <strong>{{ inspector?.usage.outputTokens ?? 0 }}</strong>
        </div>
      </section>

      <section class="ai-inspector__section" data-testid="ai-assistant-inspector-timeline">
        <header>Timeline</header>
        <ol class="ai-mini-timeline">
          <li v-for="event in inspector?.eventTimeline || []" :key="event.id">
            <span>{{ event.sequence }}</span>
            <strong>{{ event.type }}</strong>
          </li>
        </ol>
      </section>
    </aside>
  </section>
</template>

<script setup lang="ts">
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CodeOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  SendOutlined,
  ThunderboltOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import { computed, onMounted, ref } from 'vue'

import {
  approveAiAssistantApproval,
  createAiAssistantSession,
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
const sessionTitle = ref('AI Assistant')
const runId = ref<number | null>(null)
const runStatus = ref('IDLE')
const draft = ref('')
const sending = ref(false)
const events = ref<AiAssistantEvent[]>([])
const inspector = ref<AiAssistantRunInspector | null>(null)

const timeline = computed(() => buildAiAssistantTimeline(events.value))
const runStatusLabel = computed(() => (sending.value ? 'Running' : runStatus.value))
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
  const session = await createAiAssistantSession({ title: 'AI Assistant' })
  await loadSessions()
  await selectSession(session.id)
}

async function selectSession(nextSessionId: number) {
  const selected = sessions.value.find((session) => session.id === nextSessionId)
  sessionId.value = nextSessionId
  sessionTitle.value = selected?.title || 'AI Assistant'
  await loadSessionRuns(nextSessionId)
}

async function loadSessionRuns(nextSessionId: number, preferredRunId?: number) {
  runs.value = (await listAiAssistantSessionRuns(nextSessionId)).list
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

async function submit() {
  const message = draft.value.trim()
  if (!message) return
  if (!sessionId.value) {
    await createConversation()
  }
  if (!sessionId.value) return
  sending.value = true
  try {
    const asksForUpdate = message.toLowerCase().includes('update')
    const result = await sendAiAssistantMessage(sessionId.value, {
      message,
      idempotencyKey: `ui-${Date.now()}`,
      approvalMode: 'smart_approval',
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
  await denyAiAssistantApproval(approvalId, { actorId: 'operator-ui', reason: 'Denied from UI' })
  if (runId.value) await loadRunInspector(runId.value)
}

function runTitle(run: AiAssistantRun) {
  const message = typeof run.input?.message === 'string' ? run.input.message : 'Assistant run'
  return message.length > 42 ? `${message.slice(0, 39)}...` : message
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
</script>

<style scoped>
.ai-shell {
  min-height: 42rem;
  display: grid;
  grid-template-columns: 15rem minmax(0, 1fr) 18rem;
  gap: 1rem;
  padding: 1rem;
  background: var(--color-bg-page, #f8f9fc);
  color: var(--color-text-primary, #0f1117);
  border-radius: var(--radius-lg, 0.5rem);
}

.ai-shell__side,
.ai-inspector,
.ai-console {
  min-width: 0;
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
  background: var(--color-bg-surface, #ffffff);
  box-shadow: var(--shadow-xs, 0 0.0625rem 0.125rem rgba(15, 15, 30, 0.06));
}

.ai-shell__side,
.ai-inspector {
  padding: 0.75rem;
}

.ai-shell__brand,
.ai-new-session,
.ai-session,
.ai-run,
.ai-console__top,
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

.ai-new-session,
.ai-session,
.ai-run {
  width: 100%;
  gap: 0.5rem;
  color: inherit;
  text-align: left;
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
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
  flex-direction: column;
  gap: 0.5rem;
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

.ai-session,
.ai-run {
  padding: 0.625rem;
  background: var(--color-bg-surface, #ffffff);
}

.ai-session.active,
.ai-run.active {
  border-color: var(--color-primary-300, #a5b4fc);
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
  grid-template-rows: auto minmax(24rem, 1fr) auto;
}

.ai-console__top {
  justify-content: space-between;
  gap: 1rem;
  padding: 0.875rem 1rem;
  border-bottom: 0.0625rem solid var(--color-border-default, #e3e6ef);
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
  overflow: auto;
  padding: 1rem;
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
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
  border-radius: var(--radius-lg, 0.5rem);
}

.ai-event__head {
  gap: 0.5rem;
  font-weight: 700;
}

.ai-event__head small {
  margin-left: auto;
  color: var(--color-text-tertiary, #8b92a8);
}

.ai-event__body p {
  margin: 0.5rem 0 0;
  color: var(--color-text-secondary, #4b5268);
}

.ai-event__payload {
  margin: 0.625rem 0 0;
  padding: 0.625rem;
  overflow: auto;
  color: var(--color-text-secondary, #4b5268);
  background: var(--color-bg-page, #f8f9fc);
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
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
  border-color: var(--color-warning-500, #f59e0b);
  background: var(--color-warning-50, #fffbeb);
}

.tone-danger .ai-event__body,
.ai-inspector-row.danger {
  border-color: var(--color-danger-500, #ef4444);
  background: var(--color-danger-50, #fef2f2);
}

.tone-success .ai-event__body {
  border-color: var(--color-success-500, #10b981);
  background: var(--color-success-50, #ecfdf5);
}

.ai-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 2.75rem;
  gap: 0.625rem;
  padding: 0.875rem 1rem;
  border-top: 0.0625rem solid var(--color-border-default, #e3e6ef);
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
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
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
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
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
    grid-template-columns: 1fr;
  }
}
</style>
