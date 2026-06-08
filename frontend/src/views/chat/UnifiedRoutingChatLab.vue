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
      </section>

      <section class="lab-panel">
        <div class="panel-heading panel-heading-between">
          <span class="panel-heading-title">
            <ChatLineRound class="panel-heading-icon" />
            <span>意图样例</span>
          </span>
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
        </div>
        <div v-if="showIntentSamples" class="sop-list">
          <button
            v-for="scenario in AIRLINE_SOP_SCENARIOS"
            :key="scenario.id"
            type="button"
            class="sop-option"
            :class="{ active: selectedScenarioId === scenario.id }"
            @click="selectedScenarioId = scenario.id"
          >
            <span class="sop-short">{{ scenario.shortLabel }}</span>
            <span class="sop-label">{{ scenario.label }}</span>
          </button>
        </div>
      </section>

      <section v-if="showIntentSamples" class="lab-panel">
        <div class="panel-heading">触发样例</div>
        <div class="sample-stack">
          <button
            v-for="sample in selectedScenario?.triggerUtterances ?? []"
            :key="sample"
            type="button"
            class="sample-chip"
            :disabled="sending"
            @click="sendMessage(sample)"
          >
            {{ sample }}
          </button>
        </div>
      </section>

      <section v-if="showIntentSamples" class="lab-panel">
        <div class="panel-heading">流程回复</div>
        <div class="sample-stack">
          <button
            v-for="sample in selectedScenario?.sampleReplies ?? []"
            :key="sample"
            type="button"
            class="sample-chip"
            :disabled="sending"
            @click="sendMessage(sample)"
          >
            {{ sample }}
          </button>
        </div>
      </section>
    </aside>

    <main class="lab-chat">
      <header class="lab-chat-header">
        <div>
          <h1>统一路由对话</h1>
          <p>自由对话 · {{ selectedScenario?.label ?? '意图样例' }} · {{ lastRouteAction }}</p>
        </div>
        <el-tag size="small" :type="sessionId ? 'success' : 'info'" effect="light">
          {{ sessionId ? 'Runtime Ready' : 'Waiting' }}
        </el-tag>
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
            <div class="message-content">{{ message.content }}</div>
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
            <dt>reason</dt>
            <dd>{{ latestTurn?.routeDecision.reason ?? '-' }}</dd>
          </div>
        </dl>
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
} from '@element-plus/icons-vue'
import {
  createRuntimeLabSession,
  listRuntimeLabEvents,
  listRuntimeLabTasks,
  postRuntimeLabMessage,
} from '@/api/runtimeLab'
import type { RuntimeLabEvent, RuntimeLabTask, RuntimeLabTurn } from '@/api/runtimeLab'
import {
  AIRLINE_SOP_SCENARIOS,
  buildRuntimeLabTranscriptRow,
  buildUserTranscriptRow,
  getAirlineSopScenario,
} from './unifiedRoutingChatLab'
import type { RuntimeLabTranscriptRow } from './unifiedRoutingChatLab'

const router = useRouter()
const selectedScenarioId = ref(AIRLINE_SOP_SCENARIOS[0]?.id ?? '')
const showIntentSamples = ref(true)
const inputText = ref('')
const sending = ref(false)
const creatingSession = ref(false)
const sessionId = ref<number | null>(null)
const transcript = ref<RuntimeLabTranscriptRow[]>([])
const tasks = ref<RuntimeLabTask[]>([])
const events = ref<RuntimeLabEvent[]>([])
const latestTurn = ref<RuntimeLabTurn | null>(null)
const messagesEl = ref<HTMLElement>()

const selectedScenario = computed(() => getAirlineSopScenario(selectedScenarioId.value))
const lastRouteAction = computed(() => latestTurn.value?.routeDecision.action ?? '待开始')

onMounted(() => {
  void createFreshSession()
})

function openOrdinaryChat() {
  router.push('/chat')
}

async function createFreshSession() {
  creatingSession.value = true
  try {
    const session = await createRuntimeLabSession()
    sessionId.value = session.id
    transcript.value = []
    tasks.value = []
    events.value = []
    latestTurn.value = null
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建实验会话失败')
  } finally {
    creatingSession.value = false
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
  await scrollToBottom()

  try {
    const turn = await postRuntimeLabMessage(currentSessionId, {
      message: content,
      idempotencyKey: uid('front-turn'),
    })
    latestTurn.value = turn
    transcript.value.push(buildRuntimeLabTranscriptRow(turn))
    await refreshLedger(currentSessionId, turn)
  } catch (error) {
    transcript.value.push({
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
  try {
    const [taskResult, eventResult] = await Promise.all([
      listRuntimeLabTasks(currentSessionId),
      listRuntimeLabEvents(currentSessionId),
    ])
    tasks.value = taskResult.list
    events.value = eventResult.list
  } catch {
    // The turn payload is sufficient for the transcript; ledger refresh is best effort.
  }
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

.system-stack,
.sop-list,
.sample-stack,
.task-stack,
.event-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.system-option,
.sop-option,
.sample-chip {
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
.sop-option.active {
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

.session-id,
.muted-line {
  font-size: 0.75rem;
  color: var(--color-text-tertiary);
}

.sop-option {
  display: grid;
  grid-template-columns: 2.25rem 1fr;
  align-items: center;
  gap: 0.625rem;
  padding: 0.625rem;
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

.send-button {
  width: 100%;
}

.sample-chip {
  padding: 0.5rem 0.625rem;
  font-size: 0.75rem;
}

.sample-chip:disabled {
  cursor: not-allowed;
  opacity: 0.5;
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
