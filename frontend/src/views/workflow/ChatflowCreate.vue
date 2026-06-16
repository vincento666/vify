<template>
  <div class="chatflow-create">
    <WorkflowModuleTabs />

    <div class="page-header">
      <div>
        <h2 class="page-title">{{ pageTitle }}</h2>
        <p class="page-desc">对话流程画布入口，复用工作流节点与运行基础设施</p>
      </div>
      <div class="header-actions">
        <a-button :loading="saving" type="primary" @click="saveChatflow">保存 Chatflow</a-button>
        <a-button @click="$router.push({ name: 'HifyChatflows' })">返回列表</a-button>
      </div>
    </div>

    <section class="canvas-shell" data-testid="chatflow-canvas">
      <div class="canvas-sidebar">
        <div class="panel-title">节点</div>
        <button class="node-row" type="button">Start</button>
        <button class="node-row" type="button">LLM</button>
        <button class="node-row" type="button">End</button>

        <div class="variable-panel" data-testid="chatflow-variable-panel">
          <div class="panel-title">变量</div>
          <section v-for="scope in variableScopes" :key="scope.title" class="variable-scope">
            <div class="scope-title">{{ scope.title }}</div>
            <button
              v-for="item in scope.items"
              :key="item.reference"
              type="button"
              @click="insertVariable(item.reference)"
            >
              <span>{{ item.label }}</span>
              <code>{{ item.reference }}</code>
            </button>
          </section>
        </div>
      </div>
      <div class="canvas-stage">
        <div class="stage-node start-node">
          <strong>START</strong>
          <span v-for="item in startVariables" :key="item">{{ item }}</span>
        </div>
        <div class="stage-line" />
        <div class="stage-node end-node">
          <strong>END</strong>
          <span>str.output</span>
        </div>
      </div>
      <div class="canvas-inspector">
        <div class="panel-title">配置</div>
        <label>名称</label>
        <a-input v-model:value="form.name" placeholder="Chatflow 名称" />
        <div class="field-row">
          <label>回复模板</label>
          <a-button size="small" @click="variableSelectorOpen = !variableSelectorOpen">变量</a-button>
        </div>
        <a-textarea
          :value="replyTemplate"
          :rows="5"
          placeholder="可插入 {{sys.query}} 等变量"
          @update:value="setReplyTemplate"
        />
        <div v-if="variableSelectorOpen" class="variable-popover">
          <section v-for="scope in variableScopes" :key="scope.title" class="variable-scope">
            <div class="scope-title">{{ scope.title }}</div>
            <button
              v-for="item in scope.items"
              :key="item.reference"
              type="button"
              @click="insertVariable(item.reference)"
            >
              <span>{{ item.label }}</span>
              <code>{{ item.reference }}</code>
            </button>
          </section>
        </div>
        <div class="conversation-test-panel" data-testid="chatflow-test-panel">
          <div class="panel-title">对话试运行</div>
          <label>用户消息</label>
          <a-textarea v-model:value="testProfile.message" :rows="3" placeholder="输入用户消息" />
          <div class="profile-grid">
            <a-input v-model:value="testProfile.conversationId" placeholder="conversation_id" />
            <a-input v-model:value="testProfile.userId" placeholder="user_id" />
            <a-select :virtual="false" v-model:value="testProfile.channel" placeholder="channel">
              <a-select-option value="web">web</a-select-option>
              <a-select-option value="api">api</a-select-option>
              <a-select-option value="feishu">feishu</a-select-option>
              <a-select-option value="dingtalk">dingtalk</a-select-option>
            </a-select>
          </div>
          <a-button :loading="running" type="primary" @click="runConversationTest">发送测试消息</a-button>
          <div v-if="conversationResult" class="conversation-result">
            <div class="message-bubble user">{{ testProfile.message }}</div>
            <div class="message-bubble assistant">{{ conversationResult }}</div>
          </div>
        </div>
        <div class="publish-shell" data-testid="chatflow-publish-shell">
          <div class="panel-title">发布 / Open API</div>
          <dl class="shell-fields">
            <div v-for="field in openShell.channelFields" :key="field.label">
              <dt>{{ field.label }}</dt>
              <dd>{{ field.value }}</dd>
            </div>
            <div>
              <dt>Endpoint</dt>
              <dd><code>{{ openShell.endpoint }}</code></dd>
            </div>
            <div>
              <dt>最近试运行</dt>
              <dd>{{ lastRunStatus || '未运行' }}</dd>
            </div>
            <div>
              <dt>Run ID</dt>
              <dd>{{ lastRunId || '暂无' }}</dd>
            </div>
            <div>
              <dt>状态</dt>
              <dd>{{ chatflowStatus }}</dd>
            </div>
          </dl>
          <ul v-if="publishGate.reasons.length" class="publish-reasons">
            <li v-for="reason in publishGate.reasons" :key="reason">{{ reason }}</li>
          </ul>
          <a-button
            :disabled="!publishGate.allowed"
            :loading="publishing"
            type="primary"
            @click="publishChatflow"
          >
            发布 Chatflow
          </a-button>
        </div>
        <p>当前资源类型：CHATFLOW。Chatflow 变量、测试运行和发布门禁将在 Spec 012 后续 slice 逐步接入。</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'

import { createChatflow, getChatflow, runChatflow, updateChatflow, type WorkflowDetail } from '@/api/workflow'
import { buildChatflowVariableScopes, insertChatflowVariableReference } from './chatflowVariables'
import { buildChatflowOpenShell, evaluateChatflowPublishGate } from './chatflowPublish'
import { buildChatflowRunInput } from './chatflowRunProfile'
import {
  createDefaultChatflowGraph,
  hydrateWorkflowGraph,
  serializeWorkflowGraph,
  type WorkflowCanvasGraph,
} from './flowGraph'
import WorkflowModuleTabs from './WorkflowModuleTabs.vue'

const route = useRoute()
const router = useRouter()
const chatflowId = computed(() => String(route.params.id || ''))
const numericChatflowId = computed(() => Number(route.params.id || 0))
const isEditing = computed(() => numericChatflowId.value > 0)
const form = ref({ name: '', description: '通过画布创建的 Chatflow' })
const graph = ref<WorkflowCanvasGraph>(createDefaultChatflowGraph())
const replyTemplate = ref('')
const variableSelectorOpen = ref(false)
const saving = ref(false)
const running = ref(false)
const publishing = ref(false)
const chatflowStatus = ref('DRAFT')
const lastRunStatus = ref('')
const lastRunId = ref(0)
const dirtySinceTestRun = ref(true)
const conversationResult = ref('')
const testProfile = ref({
  message: '你好，帮我查订单',
  conversationId: 'conv-demo',
  userId: 'user-demo',
  channel: 'web',
  round: 1,
})
const variableScopes = buildChatflowVariableScopes()
const pageTitle = computed(() => {
  if (!isEditing.value) return '新建 Chatflow'
  return form.value.name || `Chatflow #${chatflowId.value}`
})
const startVariables = computed(() => {
  const start = graph.value.nodes.find((node) => node.nodeKey === 'start')
  const values = start?.config.outputVariables
  return Array.isArray(values) ? values.map(String) : []
})
const openShell = computed(() => buildChatflowOpenShell({
  chatflowId: numericChatflowId.value,
  channel: testProfile.value.channel,
}))
const publishGate = computed(() => evaluateChatflowPublishGate({
  lastRunStatus: lastRunStatus.value,
  dirtySinceTestRun: dirtySinceTestRun.value,
}))

function readReplyTemplate(nextGraph: WorkflowCanvasGraph) {
  const end = nextGraph.nodes.find((node) => node.nodeKey === 'end')
  return String(end?.config.output || '')
}

function setReplyTemplate(value: string | number) {
  replyTemplate.value = String(value)
  graph.value = {
    ...graph.value,
    nodes: graph.value.nodes.map((node) =>
      node.nodeKey === 'end'
        ? { ...node, config: { ...node.config, outputVariable: 'output', output: replyTemplate.value } }
        : node,
    ),
  }
  markChatflowDirty()
}

function insertVariable(reference: string) {
  setReplyTemplate(insertChatflowVariableReference(replyTemplate.value, reference))
  variableSelectorOpen.value = false
}

async function loadChatflow() {
  if (!isEditing.value) {
    graph.value = createDefaultChatflowGraph()
    form.value = { name: '', description: '通过画布创建的 Chatflow' }
    replyTemplate.value = ''
    chatflowStatus.value = 'DRAFT'
    dirtySinceTestRun.value = true
    return
  }
  try {
    const detail = await getChatflow(numericChatflowId.value) as WorkflowDetail
    form.value = { name: detail.name, description: detail.description || '' }
    chatflowStatus.value = detail.status
    graph.value = hydrateWorkflowGraph(detail.nodes, detail.edges)
    replyTemplate.value = readReplyTemplate(graph.value)
    dirtySinceTestRun.value = true
  } catch {
    graph.value = createDefaultChatflowGraph()
    form.value = { name: '', description: '通过画布创建的 Chatflow' }
    replyTemplate.value = ''
    chatflowStatus.value = 'DRAFT'
    dirtySinceTestRun.value = true
  }
}

async function saveChatflow() {
  if (!form.value.name.trim()) {
    message.warning('请输入 Chatflow 名称')
    return 0
  }
  const payload = serializeWorkflowGraph(graph.value)
  saving.value = true
  try {
    if (isEditing.value) {
      await updateChatflow(numericChatflowId.value, {
        name: form.value.name,
        description: form.value.description,
        nodes: payload.nodes,
        edges: payload.edges,
      })
      message.success('Chatflow 已保存')
      return numericChatflowId.value
    } else {
      const created = await createChatflow({
        name: form.value.name,
        description: form.value.description,
        nodes: payload.nodes,
        edges: payload.edges,
      }) as WorkflowDetail
      chatflowStatus.value = created.status
      message.success('Chatflow 创建成功')
      await router.replace({ name: 'HifyChatflowsCanvas', params: { id: created.id } })
      return created.id
    }
  } catch (e: any) {
    message.error(e?.message || '保存失败')
    return 0
  } finally {
    saving.value = false
  }
}

async function ensureSavedChatflow() {
  return await saveChatflow()
}

async function runConversationTest() {
  if (!testProfile.value.message.trim()) {
    message.warning('请输入用户消息')
    return
  }

  const id = await ensureSavedChatflow()
  if (!id) return

  running.value = true
  conversationResult.value = ''
  try {
    const result = await runChatflow(id, buildChatflowRunInput(testProfile.value)) as any
    const output = result?.output || {}
    conversationResult.value = String(output.output ?? JSON.stringify(output))
    lastRunStatus.value = String(result?.status || '')
    lastRunId.value = Number(result?.runId || 0)
    dirtySinceTestRun.value = false
  } catch (e: any) {
    lastRunStatus.value = 'FAILED'
    conversationResult.value = e?.message || '运行失败'
  } finally {
    running.value = false
  }
}

async function publishChatflow() {
  if (!publishGate.value.allowed) {
    message.warning(publishGate.value.reasons[0] || '发布检查未通过')
    return
  }

  const id = await saveChatflow()
  if (!id) return

  publishing.value = true
  try {
    await updateChatflow(id, { status: 'PUBLISHED' })
    chatflowStatus.value = 'PUBLISHED'
    message.success('Chatflow 已发布')
  } catch (e: any) {
    message.error(e?.message || '发布失败')
  } finally {
    publishing.value = false
  }
}

function markChatflowDirty() {
  dirtySinceTestRun.value = true
  lastRunStatus.value = ''
  lastRunId.value = 0
  conversationResult.value = ''
}

watch(() => route.params.id, loadChatflow)
onMounted(loadChatflow)
</script>

<style scoped>
.chatflow-create {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.125rem;
}

.header-actions {
  display: flex;
  gap: 0.625rem;
}

.page-title {
  margin: 0 0 0.25rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.page-desc {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--color-text-secondary);
}

.canvas-shell {
  height: calc(100vh - 11rem);
  min-height: 32.5rem;
  display: grid;
  grid-template-columns: 13.75rem minmax(26.25rem, 1fr) 17.5rem;
  border: 1px solid var(--color-border-default);
  border-radius: 0.5rem;
  overflow: hidden;
  background: #f7f8fb;
}

.canvas-sidebar,
.canvas-inspector {
  padding: 1rem;
  background: #fff;
}

.canvas-sidebar {
  border-right: 1px solid var(--color-border-default);
}

.canvas-inspector {
  border-left: 1px solid var(--color-border-default);
  font-size: 0.8125rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.canvas-inspector label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--color-text-primary);
  font-weight: 700;
}

.panel-title {
  margin-bottom: 0.75rem;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.node-row {
  width: 100%;
  height: 2.25rem;
  margin-bottom: 0.5rem;
  border: 1px solid var(--color-border-default);
  border-radius: 0.375rem;
  background: #fff;
  color: var(--color-text-primary);
  text-align: left;
  padding: 0 0.75rem;
  cursor: pointer;
}

.variable-panel {
  margin-top: 1.125rem;
}

.variable-scope {
  margin-bottom: 0.75rem;
}

.scope-title {
  margin-bottom: 0.375rem;
  color: #7b8498;
  font-size: 0.75rem;
  font-weight: 700;
}

.variable-scope button {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.125rem;
  margin-bottom: 0.3125rem;
  padding: 0.4375rem 0.5rem;
  border: 0;
  border-radius: 0.4375rem;
  background: #f6f7fb;
  color: #30364a;
  cursor: pointer;
}

.variable-scope button:hover {
  background: #eef0ff;
}

.variable-scope code {
  color: #5d5ff6;
  font-size: 0.6875rem;
}

.field-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 1rem 0 0.5rem;
}

.field-row label {
  margin-bottom: 0;
}

.variable-popover {
  max-height: 16.25rem;
  margin-top: 0.5rem;
  padding: 0.625rem;
  border: 1px solid #dfe3ee;
  border-radius: 0.625rem;
  overflow: auto;
  background: #fff;
  box-shadow: 0 0.625rem 1.75rem rgba(34, 41, 63, 0.12);
}

.conversation-test-panel {
  margin-top: 1.125rem;
  padding-top: 0.875rem;
  border-top: 1px solid #edf0f6;
}

.publish-shell {
  margin-top: 1.125rem;
  padding-top: 0.875rem;
  border-top: 1px solid #edf0f6;
}

.shell-fields {
  margin: 0 0 0.75rem;
}

.shell-fields div {
  display: flex;
  justify-content: space-between;
  gap: 0.625rem;
  padding: 0.4375rem 0;
  border-bottom: 1px solid #f0f2f7;
}

.shell-fields dt {
  color: #858ea2;
  font-size: 0.75rem;
  font-weight: 700;
}

.shell-fields dd {
  margin: 0;
  max-width: 10.625rem;
  overflow-wrap: anywhere;
  color: #2f3548;
  font-size: 0.75rem;
  font-weight: 700;
  text-align: right;
}

.shell-fields code {
  color: #5d5ff6;
  font-size: 0.6875rem;
}

.publish-reasons {
  margin: 0 0 0.75rem;
  padding-left: 1.125rem;
  color: #c23b3b;
  font-size: 0.75rem;
  line-height: 1.7;
}

.profile-grid {
  display: grid;
  gap: 0.5rem;
  margin: 0.625rem 0;
}

.conversation-result {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.message-bubble {
  max-width: 100%;
  padding: 0.5625rem 0.625rem;
  border-radius: 0.625rem;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.message-bubble.user {
  align-self: flex-end;
  background: #eef0ff;
  color: #3538a8;
}

.message-bubble.assistant {
  align-self: flex-start;
  background: #f4f6fb;
  color: #2f3548;
}

.canvas-stage {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2.625rem;
  background-image:
    linear-gradient(#e6e9f0 1px, transparent 1px),
    linear-gradient(90deg, #e6e9f0 1px, transparent 1px);
  background-size: 1.5rem 1.5rem;
}

.stage-node {
  width: 11.25rem;
  min-height: 4.5rem;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  border-radius: 0.5rem;
  border: 1px solid #d9dde8;
  background: #fff;
  font-size: 0.8125rem;
  font-weight: 700;
  color: #27324a;
  box-shadow: 0 0.5rem 1.375rem rgba(39, 50, 74, 0.08);
}

.stage-node strong {
  font-size: 0.8125rem;
}

.stage-node span {
  max-width: 9.375rem;
  overflow: hidden;
  padding: 0.1875rem 0.4375rem;
  border-radius: 0.3125rem;
  background: #eef1f7;
  color: #525c73;
  font-size: 0.6875rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.start-node {
  border-color: #75d19a;
}

.end-node {
  border-color: #f0a7a7;
}

.stage-line {
  width: 4.5rem;
  height: 0.125rem;
  background: #8792a8;
}

@media (max-width: 900px) {
  .canvas-shell {
    grid-template-columns: 1fr;
    height: auto;
  }

  .canvas-sidebar,
  .canvas-inspector {
    border: 0;
  }

  .canvas-stage {
    min-height: 20rem;
  }
}
</style>
