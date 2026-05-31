<template>
  <div class="chatflow-create">
    <WorkflowModuleTabs />

    <div class="page-header">
      <div>
        <h2 class="page-title">{{ pageTitle }}</h2>
        <p class="page-desc">对话流程画布入口，复用工作流节点与运行基础设施</p>
      </div>
      <div class="header-actions">
        <el-button :loading="saving" type="primary" @click="saveChatflow">保存 Chatflow</el-button>
        <el-button @click="$router.push('/chatflows')">返回列表</el-button>
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
        <el-input v-model="form.name" placeholder="Chatflow 名称" />
        <div class="field-row">
          <label>回复模板</label>
          <el-button size="small" @click="variableSelectorOpen = !variableSelectorOpen">变量</el-button>
        </div>
        <el-input
          :model-value="replyTemplate"
          type="textarea"
          :rows="5"
          placeholder="可插入 {{sys.query}} 等变量"
          @update:model-value="setReplyTemplate"
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
          <el-input v-model="testProfile.message" type="textarea" :rows="3" placeholder="输入用户消息" />
          <div class="profile-grid">
            <el-input v-model="testProfile.conversationId" placeholder="conversation_id" />
            <el-input v-model="testProfile.userId" placeholder="user_id" />
            <el-select v-model="testProfile.channel" placeholder="channel">
              <el-option label="web" value="web" />
              <el-option label="api" value="api" />
              <el-option label="feishu" value="feishu" />
              <el-option label="dingtalk" value="dingtalk" />
            </el-select>
          </div>
          <el-button :loading="running" type="primary" @click="runConversationTest">发送测试消息</el-button>
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
          <el-button
            :disabled="!publishGate.allowed"
            :loading="publishing"
            type="primary"
            @click="publishChatflow"
          >
            发布 Chatflow
          </el-button>
        </div>
        <p>当前资源类型：CHATFLOW。Chatflow 变量、测试运行和发布门禁将在 Spec 012 后续 slice 逐步接入。</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

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
    ElMessage.warning('请输入 Chatflow 名称')
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
      ElMessage.success('Chatflow 已保存')
      return numericChatflowId.value
    } else {
      const created = await createChatflow({
        name: form.value.name,
        description: form.value.description,
        nodes: payload.nodes,
        edges: payload.edges,
      }) as WorkflowDetail
      chatflowStatus.value = created.status
      ElMessage.success('Chatflow 创建成功')
      await router.replace(`/chatflows/${created.id}/canvas`)
      return created.id
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
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
    ElMessage.warning('请输入用户消息')
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
    ElMessage.warning(publishGate.value.reasons[0] || '发布检查未通过')
    return
  }

  const id = await saveChatflow()
  if (!id) return

  publishing.value = true
  try {
    await updateChatflow(id, { status: 'PUBLISHED' })
    chatflowStatus.value = 'PUBLISHED'
    ElMessage.success('Chatflow 已发布')
  } catch (e: any) {
    ElMessage.error(e?.message || '发布失败')
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
  margin-bottom: 18px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.page-desc {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.canvas-shell {
  height: calc(100vh - 176px);
  min-height: 520px;
  display: grid;
  grid-template-columns: 220px minmax(420px, 1fr) 280px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
  background: #f7f8fb;
}

.canvas-sidebar,
.canvas-inspector {
  padding: 16px;
  background: #fff;
}

.canvas-sidebar {
  border-right: 1px solid var(--el-border-color-lighter);
}

.canvas-inspector {
  border-left: 1px solid var(--el-border-color-lighter);
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-secondary);
}

.canvas-inspector label {
  display: block;
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
  font-weight: 700;
}

.panel-title {
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.node-row {
  width: 100%;
  height: 36px;
  margin-bottom: 8px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: #fff;
  color: var(--el-text-color-primary);
  text-align: left;
  padding: 0 12px;
  cursor: pointer;
}

.variable-panel {
  margin-top: 18px;
}

.variable-scope {
  margin-bottom: 12px;
}

.scope-title {
  margin-bottom: 6px;
  color: #7b8498;
  font-size: 12px;
  font-weight: 700;
}

.variable-scope button {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  margin-bottom: 5px;
  padding: 7px 8px;
  border: 0;
  border-radius: 7px;
  background: #f6f7fb;
  color: #30364a;
  cursor: pointer;
}

.variable-scope button:hover {
  background: #eef0ff;
}

.variable-scope code {
  color: #5d5ff6;
  font-size: 11px;
}

.field-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0 8px;
}

.field-row label {
  margin-bottom: 0;
}

.variable-popover {
  max-height: 260px;
  margin-top: 8px;
  padding: 10px;
  border: 1px solid #dfe3ee;
  border-radius: 10px;
  overflow: auto;
  background: #fff;
  box-shadow: 0 10px 28px rgba(34, 41, 63, 0.12);
}

.conversation-test-panel {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #edf0f6;
}

.publish-shell {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #edf0f6;
}

.shell-fields {
  margin: 0 0 12px;
}

.shell-fields div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 0;
  border-bottom: 1px solid #f0f2f7;
}

.shell-fields dt {
  color: #858ea2;
  font-size: 12px;
  font-weight: 700;
}

.shell-fields dd {
  margin: 0;
  max-width: 170px;
  overflow-wrap: anywhere;
  color: #2f3548;
  font-size: 12px;
  font-weight: 700;
  text-align: right;
}

.shell-fields code {
  color: #5d5ff6;
  font-size: 11px;
}

.publish-reasons {
  margin: 0 0 12px;
  padding-left: 18px;
  color: #c23b3b;
  font-size: 12px;
  line-height: 1.7;
}

.profile-grid {
  display: grid;
  gap: 8px;
  margin: 10px 0;
}

.conversation-result {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.message-bubble {
  max-width: 100%;
  padding: 9px 10px;
  border-radius: 10px;
  font-size: 13px;
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
  gap: 42px;
  background-image:
    linear-gradient(#e6e9f0 1px, transparent 1px),
    linear-gradient(90deg, #e6e9f0 1px, transparent 1px);
  background-size: 24px 24px;
}

.stage-node {
  width: 180px;
  min-height: 72px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 8px;
  border: 1px solid #d9dde8;
  background: #fff;
  font-size: 13px;
  font-weight: 700;
  color: #27324a;
  box-shadow: 0 8px 22px rgba(39, 50, 74, 0.08);
}

.stage-node strong {
  font-size: 13px;
}

.stage-node span {
  max-width: 150px;
  overflow: hidden;
  padding: 3px 7px;
  border-radius: 5px;
  background: #eef1f7;
  color: #525c73;
  font-size: 11px;
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
  width: 72px;
  height: 2px;
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
    min-height: 320px;
  }
}
</style>
