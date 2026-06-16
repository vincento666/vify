<template>
  <div class="chat-layout">

    <!-- ── 左侧会话列表 ──────────────────────────────────── -->
    <aside class="session-sidebar">
      <div class="session-header">
        <span class="session-title">对话列表</span>
        <a-button type="primary" size="small" @click="onNewSession">
          <span class="button-icon"><PlusOutlined /></span>
          新建
        </a-button>
      </div>

      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === activeSessionId }"
          @click="selectSession(s.id)"
        >
          <div class="session-item-top">
            <span class="session-agent">{{ agentNameMap[s.agentId] ?? 'Agent' }}</span>
            <span class="session-time">{{ formatTime(s.createdAt) }}</span>
          </div>
          <div class="session-preview">{{ sessionPreviewMap[s.id] ?? '暂无消息' }}</div>
          <a-button
            class="session-delete-btn"
            type="link"
            danger
            size="small"
            @click.stop="onDeleteSession(s)"
          >
            <DeleteOutlined />
          </a-button>
        </div>

        <div v-if="sessions.length === 0" class="session-empty">暂无对话</div>
      </div>
    </aside>

    <!-- ── 右侧聊天窗口 ──────────────────────────────────── -->
    <section class="chat-main">

      <!-- 无会话占位 -->
      <div v-if="!activeSessionId" class="chat-welcome">
        <div class="welcome-icon">💬</div>
        <div class="welcome-title">选择或新建一个对话</div>
        <div class="welcome-sub">从左侧列表选择对话，或点击「新建」开始</div>
      </div>

      <template v-else>
        <!-- 顶栏 -->
        <div class="chat-topbar">
          <span class="chat-topbar-name">{{ agentNameMap[activeSession?.agentId ?? 0] ?? 'Agent' }}</span>
          <a-tag v-if="activeAgentWorkflowId" color="warning" class="chat-mode-tag hify-tag">
            工作流模式
          </a-tag>
          <a-tag v-else class="chat-mode-tag hify-tag">
            直接对话
          </a-tag>
        </div>

        <!-- 消息区域 -->
        <div class="messages-wrap" ref="messagesEl">
          <div
            v-if="messages.length === 0 && (activeAgentOpening || activeAgentSuggestedQuestions.length)"
            class="chat-entry"
          >
            <div v-if="activeAgentOpening" class="msg-row assistant">
              <div class="msg-avatar">
                <a-avatar class="chat-avatar assistant-avatar">AI</a-avatar>
              </div>
              <div class="msg-bubble">
                <div class="msg-content">{{ activeAgentOpening }}</div>
              </div>
            </div>
            <div v-if="activeAgentSuggestedQuestions.length" class="chat-suggestions">
              <button
                v-for="question in activeAgentSuggestedQuestions"
                :key="question"
                type="button"
                class="chat-suggestion"
                :disabled="streaming"
                @click="sendSuggestedQuestion(question)"
              >
                {{ question }}
              </button>
            </div>
          </div>
          <div
            v-for="msg in messages"
            :key="msg.id ?? msg._tempId"
            class="msg-row"
            :class="msg.role"
          >
            <!-- 头像 -->
            <div class="msg-avatar">
              <a-avatar v-if="msg.role === 'user'" class="chat-avatar user-avatar">我</a-avatar>
              <a-avatar v-else class="chat-avatar assistant-avatar">AI</a-avatar>
            </div>

            <!-- 气泡 -->
            <div class="msg-bubble" :class="{ error: msg._error, loading: msg._loading }">
              <!-- 加载动画 -->
              <span v-if="msg._loading && !msg.content" class="typing-dots">
                <span /><span /><span />
              </span>
              <!-- assistant 渲染 Markdown，user 纯文本 -->
              <div
                v-else-if="msg.role === 'assistant'"
                class="msg-content markdown-body"
                v-html="renderMarkdown(msg.content)"
              />
              <div v-else class="msg-content">{{ msg.content }}</div>
            </div>
          </div>
        </div>

        <!-- 底部输入区 -->
        <div class="chat-input-area">
          <a-textarea
            v-model:value="inputText"
            :auto-size="{ minRows: 1, maxRows: 5 }"
            placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            :disabled="streaming"
            @keydown.enter.exact.prevent="onSend"
          />
          <a-button
            class="send-btn"
            type="primary"
            :disabled="!inputText.trim() || streaming"
            :loading="streaming"
            @click="onSend"
          >
            {{ streaming ? '生成中' : '发送' }}
          </a-button>
        </div>
      </template>

    </section>

    <!-- 新建对话弹窗 -->
    <a-modal v-model:open="newSessionVisible" title="新建对话" width="25rem" :mask-closable="false">
      <a-form :label-col="{ style: { width: '5rem' } }">
        <a-form-item label="选择 Agent">
          <a-select v-model:value="newSessionAgentId" placeholder="请选择 Agent" class="agent-select">
            <a-select-option v-for="a in agents" :key="a.id" :value="a.id">
              <div class="agent-option-row">
                <span>{{ a.name }}</span>
                <div class="agent-option-tags">
                  <a-tag v-if="a.workflowId" color="warning" class="hify-tag">工作流</a-tag>
                  <a-tag v-if="a.knowledgeBaseId" color="success" class="hify-tag">知识库</a-tag>
                </div>
              </div>
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="newSessionVisible = false">取消</a-button>
        <a-button type="primary" :disabled="!newSessionAgentId" @click="confirmNewSession">确定</a-button>
      </template>
    </a-modal>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { marked } from 'marked'
import {
  createSession, getSessions, deleteSession,
  getMessages, streamMessage,
} from '@/api/chat'
import type { ChatSession, ChatMessage } from '@/api/chat'
import { getAgentList } from '@/api/agent'
import type { AgentListItem } from '@/api/agent'

// ── marked 配置 ───────────────────────────────────────────
marked.setOptions({ breaks: true })

// ── 消息类型（含临时字段）────────────────────────────────
interface DisplayMessage extends Partial<ChatMessage> {
  _tempId?: string
  _loading?: boolean
  _error?: boolean
  role: 'user' | 'assistant' | 'system'
  content: string
}

// ── 状态 ─────────────────────────────────────────────────
const sessions = ref<ChatSession[]>([])
const activeSessionId = ref<number | null>(null)
const messages = ref<DisplayMessage[]>([])
const inputText = ref('')
const streaming = ref(false)
const agents = ref<AgentListItem[]>([])

const newSessionVisible = ref(false)
const newSessionAgentId = ref<number | null>(null)

const messagesEl = ref<HTMLElement>()

const sessionPreviewMap = ref<Record<number, string>>({})

const agentNameMap = computed<Record<number, string>>(() => {
  const m: Record<number, string> = {}
  for (const a of agents.value) m[a.id] = a.name
  return m
})

const activeSession = computed(() => sessions.value.find(s => s.id === activeSessionId.value))
const activeAgent = computed(() => {
  const agentId = activeSession.value?.agentId
  if (!agentId) return null
  return agents.value.find(a => a.id === agentId) ?? null
})

const activeAgentWorkflowId = computed(() => {
  return activeAgent.value?.workflowId ?? null
})
const activeAgentOpening = computed(() => activeAgent.value?.openingMessage?.trim() || '')
const activeAgentSuggestedQuestions = computed(() => normalizeQuestions(activeAgent.value?.suggestedQuestions ?? []))

// ── 初始化 ────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadSessions(), loadAgents()])
  if (sessions.value.length > 0) {
    await selectSession(sessions.value[0].id)
  }
})

async function loadSessions() {
  try {
    const res = await getSessions({ pageSize: 50 })
    sessions.value = res.list
  } catch { /* ignore */ }
}

async function loadAgents() {
  try {
    const res = await getAgentList({ page: 1, pageSize: 100 })
    agents.value = res.list
  } catch { /* ignore */ }
}

// ── 切换会话 ──────────────────────────────────────────────
async function selectSession(id: number) {
  if (streaming.value) return
  activeSessionId.value = id
  messages.value = []
  try {
    const res = await getMessages(id, { page: 1, pageSize: 100 })
    messages.value = res.list.map(m => ({ ...m, role: m.role as 'user' | 'assistant' | 'system' }))
    const last = res.list[res.list.length - 1]
    if (last) sessionPreviewMap.value[id] = truncate(last.content, 30)
    await scrollToBottom()
  } catch { /* ignore */ }
}

// ── 新建会话 ──────────────────────────────────────────────
function onNewSession() {
  newSessionAgentId.value = agents.value[0]?.id ?? null
  newSessionVisible.value = true
}

async function confirmNewSession() {
  if (!newSessionAgentId.value) return
  try {
    const s = await createSession(newSessionAgentId.value)
    sessions.value.unshift(s)
    newSessionVisible.value = false
    await selectSession(s.id)
  } catch {
    message.error('创建对话失败')
  }
}

// ── 删除会话 ──────────────────────────────────────────────
async function onDeleteSession(s: ChatSession) {
  Modal.confirm({
    title: '提示',
    content: '确定删除这个对话？',
    okText: '确认',
    cancelText: '取消',
    onOk: async () => {
      await deleteSession(s.id)
      sessions.value = sessions.value.filter(x => x.id !== s.id)
      delete sessionPreviewMap.value[s.id]
      if (activeSessionId.value === s.id) {
        activeSessionId.value = null
        messages.value = []
        if (sessions.value.length > 0) await selectSession(sessions.value[0].id)
      }
    },
  })
}

// ── 发送消息 ──────────────────────────────────────────────
async function onSend() {
  const content = inputText.value.trim()
  if (!content || !activeSessionId.value || streaming.value) return

  inputText.value = ''
  streaming.value = true

  // 用户气泡
  const userMsg: DisplayMessage = { _tempId: uid(), role: 'user', content }
  messages.value.push(userMsg)
  await scrollToBottom()

  // AI 气泡（loading）
  const aiMsg: DisplayMessage = { _tempId: uid(), role: 'assistant', content: '', _loading: true }
  messages.value.push(aiMsg)
  await scrollToBottom()

  const sessionId = activeSessionId.value
  streamMessage(
    sessionId,
    content,
    (delta) => {
      aiMsg.content += delta
      aiMsg._loading = false
      scrollToBottom()
    },
    (_finishReason, _latencyMs) => {
      aiMsg._loading = false
      streaming.value = false
      sessionPreviewMap.value[sessionId] = truncate(aiMsg.content, 30)
    },
    (errMsg) => {
      aiMsg._loading = false
      aiMsg._error = true
      aiMsg.content = errMsg || 'LLM 调用失败'
      streaming.value = false
    },
  )
}

async function sendSuggestedQuestion(question: string) {
  if (streaming.value) return
  inputText.value = question
  await onSend()
}

// ── 工具函数 ──────────────────────────────────────────────
function renderMarkdown(text: string): string {
  if (!text) return ''
  return marked.parse(text) as string
}

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}分钟前`
  if (d.toDateString() === now.toDateString()) return d.toTimeString().slice(0, 5)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function truncate(text: string, len: number) {
  return text.length > len ? text.slice(0, len) + '…' : text
}

function normalizeQuestions(questions: string[]) {
  const normalized: string[] = []
  const seen = new Set<string>()
  for (const question of questions) {
    const value = String(question || '').trim()
    if (!value || seen.has(value)) continue
    seen.add(value)
    normalized.push(value)
  }
  return normalized
}

let _uid = 0
function uid() { return `tmp-${++_uid}` }
</script>

<style scoped>
/* ── 整体布局 ─────────────────────────────────────────────── */
.chat-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: var(--color-bg-page);
}

/* ── 左侧会话列表 ─────────────────────────────────────────── */
.session-sidebar {
  width: 15rem;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 0.0625rem solid var(--color-border-default);
  background: var(--color-bg-card);
}

.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 0.875rem 0.625rem;
  border-bottom: 0.0625rem solid var(--color-border-default);
  flex-shrink: 0;
}

.session-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.375rem 0;
}

.session-item {
  position: relative;
  padding: 0.625rem 0.875rem 0.625rem 0.75rem;
  cursor: pointer;
  border-left: 0.1875rem solid transparent;
  transition: background 0.15s;
}
.session-item:hover { background: var(--color-bg-hover); }
.session-item.active {
  background: rgba(99, 102, 241, 0.08);
  border-left-color: var(--color-primary);
}
.session-item:hover .session-delete-btn { opacity: 1; }

.session-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.1875rem;
}
.session-agent {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-primary);
}
.session-time {
  font-size: 0.6875rem;
  color: var(--color-text-tertiary);
}
.session-preview {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 1.25rem;
}
.session-delete-btn {
  position: absolute;
  right: 0.5rem;
  bottom: 0.625rem;
  opacity: 0;
  transition: opacity 0.15s;
  padding: 0 !important;
}

.session-empty {
  text-align: center;
  padding: 2.5rem 0;
  color: var(--color-text-tertiary);
  font-size: 0.8125rem;
}

/* ── 右侧聊天区 ───────────────────────────────────────────── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.625rem;
  color: var(--color-text-secondary);
}
.welcome-icon { font-size: 3rem; line-height: 1; }
.welcome-title { font-size: 1rem; font-weight: 600; color: var(--color-text-primary); }
.welcome-sub { font-size: 0.8125rem; }

.chat-topbar {
  height: 3rem;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0 1.25rem;
  border-bottom: 0.0625rem solid var(--color-border-default);
  background: var(--color-bg-card);
}
.chat-topbar-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.chat-mode-tag {
  margin-left: var(--space-2);
}

.messages-wrap {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.chat-entry {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  align-items: flex-start;
}

.chat-suggestions {
  display: grid;
  gap: 0.5rem;
  justify-items: start;
  margin-left: 2.5rem;
}

.chat-suggestion {
  border: 0.0625rem solid var(--color-border-default);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  border-radius: 62.4375rem;
  min-height: 1.875rem;
  padding: 0.3125rem 0.6875rem;
  font-size: 0.8125rem;
  text-align: left;
}

.chat-suggestion:hover {
  border-color: var(--color-primary-300);
  color: var(--color-primary-600);
}

.chat-suggestion:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.msg-row {
  display: flex;
  gap: 0.625rem;
  align-items: flex-start;
}
.msg-row.user { flex-direction: row-reverse; }

.msg-avatar { flex-shrink: 0; margin-top: 0.125rem; }

.chat-avatar {
  width: 1.875rem;
  height: 1.875rem;
  font-size: 0.8125rem;
}

.user-avatar {
  background: #6366f1;
}

.assistant-avatar {
  background: #8b5cf6;
}

.msg-bubble {
  width: fit-content;
  max-width: 68%;
  box-sizing: border-box;
  padding: 0.625rem 0.875rem;
  border-radius: 0.75rem;
  font-size: 0.875rem;
  line-height: 1.65;
  word-break: break-word;
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  border: 0.0625rem solid var(--color-border-default);
  box-shadow: 0 1px 0.1875rem rgba(0,0,0,0.04);
}
.msg-row.user .msg-bubble {
  background: #eaf4ff;
  color: #1e3a8a;
  border-color: #bfdbfe;
}
.msg-bubble.error {
  background: rgba(239,68,68,0.08);
  border-color: rgba(239,68,68,0.3);
  color: #ef4444;
}

/* 打字动画 */
.typing-dots {
  display: inline-flex;
  gap: 0.25rem;
  align-items: center;
  padding: 0.125rem 0;
}
.typing-dots span {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 50%;
  background: var(--color-text-tertiary);
  animation: blink 1.2s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

/* 底部输入区 */
.chat-input-area {
  flex-shrink: 0;
  display: flex;
  gap: 0.625rem;
  align-items: flex-end;
  padding: 0.875rem 1.25rem;
  border-top: 0.0625rem solid var(--color-border-default);
  background: var(--color-bg-card);
}
.chat-input-area :deep(textarea) {
  border-radius: 0.5rem;
  font-size: 0.875rem;
  padding: 0.625rem 0.875rem;
  resize: none;
}
.button-icon { display: inline-flex; }
.send-btn {
  flex-shrink: 0;
  height: 2.375rem;
  padding: 0 1.125rem;
}

.agent-select {
  width: 100%;
}

.agent-option-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  justify-content: space-between;
}

.agent-option-tags {
  display: flex;
  gap: var(--space-1);
}

/* ── Markdown 样式 ─────────────────────────────────────────── */
.markdown-body :deep(p) { margin: 0 0 0.5rem; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(code) {
  font-family: 'Fira Code', Consolas, monospace;
  font-size: 0.8125rem;
  background: rgba(99,102,241,0.1);
  padding: 0.0625rem 0.3125rem;
  border-radius: 0.25rem;
}
.markdown-body :deep(pre) {
  background: #1a1b26;
  border-radius: 0.5rem;
  padding: 0.875rem 1rem;
  overflow-x: auto;
  margin: 0.5rem 0;
}
.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: #c0caf5;
  font-size: 0.8125rem;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) { padding-left: 1.25rem; margin: 0.375rem 0; }
.markdown-body :deep(li) { margin: 0.1875rem 0; }
.markdown-body :deep(strong) { font-weight: 600; }
.markdown-body :deep(blockquote) {
  border-left: 0.1875rem solid var(--color-primary);
  margin: 0.5rem 0;
  padding: 0.25rem 0.75rem;
  color: var(--color-text-secondary);
}
</style>
