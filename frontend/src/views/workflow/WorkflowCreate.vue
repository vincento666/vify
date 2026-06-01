<template>
  <div class="workflow-canvas-page" :class="{ 'chatflow-mode': isChatflowMode }">
    <div class="canvas-topbar">
      <div class="canvas-title-wrap">
        <el-button text class="back-button" @click="router.push(listPath)">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div class="flow-icon"><Share /></div>
        <div>
          <div class="title-row">
            <el-input
              v-model="form.name"
              class="title-input"
              maxlength="100"
              :placeholder="isChatflowMode ? 'Chatflow 名称' : '工作流名称'"
            />
            <span class="flow-info">i</span>
          </div>
          <div class="save-state">{{ saveState }}</div>
        </div>
      </div>
      <div class="canvas-mode-tabs" role="tablist" aria-label="canvas lifecycle">
        <button :class="{ active: canvasTab === 'compose' }" type="button" @click="canvasTab = 'compose'">编排</button>
        <button :class="{ active: canvasTab === 'stats' }" type="button" @click="canvasTab = 'stats'">统计</button>
        <button :class="{ active: canvasTab === 'open' }" type="button" @click="openOpsPanel('api')">开放</button>
      </div>
      <div class="canvas-actions">
        <el-button @click="openTestPanel">{{ isChatflowMode ? '对话试运行' : '试运行' }}</el-button>
        <el-button @click="openOpsPanel('observe')">观测</el-button>
        <el-button type="primary" plain @click="openOpsPanel('publish')">发布</el-button>
        <el-button :loading="saving" type="primary" @click="saveCanvas">保存</el-button>
      </div>
    </div>

    <section
      class="canvas-workbench"
      :class="{ 'resource-collapsed': resourcePanelCollapsed }"
      data-testid="workflow-canvas"
    >
      <button
        class="resource-panel-toggle"
        type="button"
        :aria-label="resourcePanelCollapsed ? '展开侧栏' : '折叠侧栏'"
        @click="resourcePanelCollapsed = !resourcePanelCollapsed"
      >
        <el-icon>
          <ArrowRight v-if="resourcePanelCollapsed" />
          <ArrowLeft v-else />
        </el-icon>
      </button>

      <aside v-if="!resourcePanelCollapsed" class="canvas-resource-panel" data-testid="canvas-resource-panel">
        <div class="resource-header">
          <strong>{{ isChatflowMode ? '对话设置' : '画布概览' }}</strong>
          <span>{{ isChatflowMode ? 'Conversation runtime' : 'Canvas overview' }}</span>
        </div>

        <template v-if="isChatflowMode">
          <section class="resource-section">
            <h4>开场白</h4>
            <el-input v-model="openingText" type="textarea" :rows="3" placeholder="欢迎语" @input="markGraphDirty" />
          </section>
          <section class="resource-section">
            <h4>引导问题</h4>
            <div v-for="(_question, index) in guideQuestions" :key="index" class="question-row">
              <input v-model="guideQuestions[index]" @input="markGraphDirty" />
              <button type="button" @click="removeGuideQuestion(index)">×</button>
            </div>
            <button type="button" class="resource-action" @click="addGuideQuestion">新增问题</button>
          </section>
          <section class="resource-section" data-testid="chatflow-variable-panel">
            <h4>变量</h4>
            <div v-for="scope in chatflowVariableScopes" :key="scope.title" class="resource-group">
              <button type="button" @click="scope.open = !scope.open">
                <span>{{ scope.title }}</span>
                <small>{{ scope.description }}</small>
              </button>
              <div v-if="scope.open" class="resource-items">
                <button
                  v-for="item in scope.items"
                  :key="item.reference"
                  type="button"
                  @click="insertChatflowVariable(item.reference)"
                >
                  <span>{{ item.label }}</span>
                  <code>{{ item.reference }}</code>
                </button>
              </div>
            </div>
          </section>
        </template>

        <template v-else>
          <section class="resource-section" data-testid="workflow-overview-panel">
            <h4>画布</h4>
            <dl class="resource-stats">
              <div>
                <dt>节点</dt>
                <dd>{{ graph.nodes.length }}</dd>
              </div>
              <div>
                <dt>连线</dt>
                <dd>{{ graph.edges.length }}</dd>
              </div>
              <div>
                <dt>状态</dt>
                <dd>{{ workflowStatus }}</dd>
              </div>
            </dl>
          </section>
          <section class="resource-section">
            <h4>选中节点</h4>
            <div class="selected-node-summary">
              <strong>{{ selectedNode?.name || '未选择' }}</strong>
              <span>{{ selectedNode?.nodeKey || '-' }}</span>
            </div>
          </section>
        </template>
      </aside>

      <div
        ref="canvasStageRef"
        class="canvas-stage-shell"
        tabindex="0"
        @keydown="handleCanvasKeydown"
      >
      <VueFlow
        v-model:nodes="flowNodes"
        v-model:edges="flowEdges"
        class="coze-flow"
        :default-viewport="{ x: 0, y: 0, zoom: 1 }"
        :min-zoom="0.3"
        :max-zoom="1.6"
        :nodes-draggable="true"
        fit-view-on-init
        @connect="handleConnect"
        @node-drag-stop="handleNodeDragStop"
        @node-click="handleNodeClick"
        @pane-click="selectedNodeKey = ''"
      >
        <template #node-coze="nodeProps">
          <div
            class="coze-node"
            :class="[`node-${nodeProps.data.type.toLowerCase()}`, { selected: selectedNodeKey === nodeProps.data.nodeKey }]"
          >
            <Handle
              v-if="nodeProps.data.type !== 'START'"
              type="target"
              :position="Position.Left"
              class="node-port target-port"
            />
            <div class="node-header">
              <div class="node-type-icon" :class="`icon-${nodeProps.data.type.toLowerCase()}`">
                <component :is="nodeIcon(nodeProps.data.type)" />
              </div>
              <div class="node-title">{{ nodeProps.data.name }}</div>
            </div>
            <div class="node-line">
              <span>输入</span>
              <template v-if="nodeProps.data.type === 'START'">
                <div
                  class="node-variable-list"
                  data-testid="start-variable-list"
                  :title="startVariableTooltip(nodeProps.data.outputVariables)"
                >
                  <em
                    v-for="value in startVisibleVariables(nodeProps.data.outputVariables)"
                    :key="value"
                    class="node-variable-badge"
                  >
                    str.{{ value }}
                  </em>
                  <span
                    v-if="startHasHiddenVariables(nodeProps.data.outputVariables)"
                    class="node-variable-more"
                    data-testid="start-variable-more"
                  >
                    ...
                  </span>
                </div>
              </template>
              <template v-else-if="nodeProps.data.type === 'END'">
                <em class="orange">str.{{ nodeProps.data.outputVariable || 'output' }}</em>
              </template>
              <template v-else>
                <strong>未配置输入</strong>
              </template>
            </div>
            <div v-if="nodeProps.data.type !== 'START'" class="node-line">
              <span>输出</span>
              <em>{{ outputBadge(nodeProps.data.type, nodeProps.data.outputVariable) }}</em>
            </div>
            <Handle
              v-if="nodeProps.data.type !== 'END'"
              type="source"
              :position="Position.Right"
              class="node-port source-port"
            />
          </div>
        </template>
      </VueFlow>

      <aside v-if="selectedNode && selectedSchema" class="node-config-panel" data-testid="node-config-panel">
        <div class="config-header">
          <div class="node-type-icon" :class="`icon-${selectedNode.type.toLowerCase()}`">
            <component :is="nodeIcon(selectedNode.type)" />
          </div>
          <div>
            <h3>{{ selectedSchema.title }}</h3>
            <span>{{ selectedNode.nodeKey }}</span>
          </div>
          <button type="button" aria-label="关闭配置" @click="selectedNodeKey = ''">×</button>
        </div>

        <section v-for="section in selectedSchema.sections" :key="section.title" class="config-section">
          <div class="section-title">
            <span>⌄</span>
            {{ section.title }}
          </div>
          <div v-for="field in section.fields" :key="field.key" class="config-field">
            <div class="field-label-row">
              <label>{{ field.label }}</label>
              <button
                v-if="canUseVariable(field.key)"
                type="button"
                class="variable-trigger"
                @click="activeVariableField = activeVariableField === field.key ? '' : field.key"
              >
                变量
              </button>
            </div>
            <div v-if="field.type === 'readonly'" class="readonly-values">
              <el-tag
                v-for="value in readonlyValues(field.key)"
                :key="value"
                size="small"
                effect="plain"
              >
                {{ value }}
              </el-tag>
            </div>
            <el-input
              v-else-if="field.type === 'textarea'"
              :model-value="fieldValue(field.key)"
              :placeholder="field.placeholder"
              type="textarea"
              :rows="5"
              @update:model-value="setFieldValue(field.key, $event)"
            />
            <el-input-number
              v-else-if="field.type === 'number'"
              :model-value="Number(fieldValue(field.key) || 0)"
              :min="1"
              :max="20"
              controls-position="right"
              @update:model-value="setFieldValue(field.key, $event)"
            />
            <el-select
              v-else-if="field.type === 'select'"
              :model-value="fieldValue(field.key) || field.options?.[0]"
              @update:model-value="setFieldValue(field.key, $event)"
            >
              <el-option v-for="option in field.options || []" :key="option" :label="option" :value="option" />
            </el-select>
            <el-input
              v-else
              :model-value="fieldValue(field.key)"
              :placeholder="field.placeholder"
              @update:model-value="setFieldValue(field.key, $event)"
            />
            <div v-if="activeVariableField === field.key" class="variable-popover">
              <el-input v-model="variableSearch" size="small" placeholder="搜索变量" />
              <div v-for="group in filteredVariableGroups" :key="group.title" class="variable-group">
                <div class="variable-group-title">{{ group.title }}</div>
                <button
                  v-for="item in group.items"
                  :key="item.reference"
                  type="button"
                  @click="insertVariable(field.key, item.reference)"
                >
                  <span>{{ item.label }}</span>
                  <code>{{ item.reference }}</code>
                </button>
              </div>
            </div>
          </div>
        </section>
      </aside>

      <aside v-if="testPanelOpen" class="test-run-panel" data-testid="test-run-panel">
        <div class="config-header">
          <div class="node-type-icon icon-start"><Finished /></div>
          <div>
            <h3>试运行</h3>
            <span>从 START 节点执行当前画布</span>
          </div>
          <button type="button" aria-label="关闭试运行" @click="testPanelOpen = false">×</button>
        </div>

        <section class="config-section">
          <div class="section-title"><span>⌄</span> 输入</div>
          <div class="run-input-field">
            <label>{{ isChatflowMode ? '用户消息（sys.query）' : '用户消息（userMessage / USER_INPUT）' }}</label>
            <el-input
              v-model="testInput"
              type="textarea"
              :rows="4"
              :placeholder="isChatflowMode ? '输入用户消息' : '输入 userMessage'"
            />
          </div>
          <div v-if="isChatflowMode" class="chatflow-profile-grid">
            <div class="run-input-field compact">
              <label>会话 ID（sys.conversation_id）</label>
              <el-input v-model="testProfile.conversationId" placeholder="conversation_id" />
            </div>
            <div class="run-input-field compact">
              <label>用户 ID（sys.user_id）</label>
              <el-input v-model="testProfile.userId" placeholder="user_id" />
            </div>
            <div class="run-input-field compact">
              <label>渠道（sys.channel）</label>
              <el-select v-model="testProfile.channel" placeholder="channel">
                <el-option label="web" value="web" />
                <el-option label="api" value="api" />
                <el-option label="feishu" value="feishu" />
                <el-option label="dingtalk" value="dingtalk" />
              </el-select>
            </div>
          </div>
          <div
            v-if="isChatflowMode && !testResult && (chatflowOpeningText || activeGuideQuestions.length)"
            class="chatflow-runtime-preview"
            data-testid="chatflow-runtime-preview"
          >
            <div
              v-if="chatflowOpeningText"
              class="message-bubble assistant opening"
              data-testid="chatflow-opening-message"
            >
              {{ chatflowOpeningText }}
            </div>
            <div
              v-if="activeGuideQuestions.length"
              class="chatflow-suggested-questions"
              data-testid="chatflow-suggested-questions"
            >
              <div class="chatflow-suggested-title">猜你想问</div>
              <div class="chatflow-guide-list">
                <button
                  v-for="question in activeGuideQuestions"
                  :key="question"
                  type="button"
                  data-testid="chatflow-guide-question"
                  @click="applyGuideQuestion(question)"
                >
                  {{ question }}
                </button>
              </div>
            </div>
          </div>
        </section>

        <section v-if="validationErrors.length" class="config-section">
          <div class="section-title validation-title"><span>!</span> 校验失败</div>
          <ul class="validation-list">
            <li v-for="error in validationErrors" :key="error">{{ error }}</li>
          </ul>
        </section>

        <section v-if="testResult" class="config-section">
          <div class="section-title"><span>✓</span> 运行结果</div>
          <div class="run-summary">
            <span class="run-status" :class="{ success: testResult.status === 'SUCCEEDED' }">{{ testResult.status }}</span>
            <span v-if="testResult.runId">Run #{{ testResult.runId }}</span>
          </div>
          <div v-if="isChatflowMode" class="conversation-result">
            <div
              v-if="chatflowOpeningText"
              class="message-bubble assistant opening"
              data-testid="chatflow-opening-message"
            >
              {{ chatflowOpeningText }}
            </div>
            <div
              v-if="activeGuideQuestions.length"
              class="chatflow-suggested-questions"
              data-testid="chatflow-suggested-questions"
            >
              <div class="chatflow-suggested-title">猜你想问</div>
              <div class="chatflow-guide-list">
                <button
                  v-for="question in activeGuideQuestions"
                  :key="question"
                  type="button"
                  data-testid="chatflow-guide-question"
                  @click="applyGuideQuestion(question)"
                >
                  {{ question }}
                </button>
              </div>
            </div>
            <div class="message-bubble user" data-testid="chatflow-user-message">{{ testInput }}</div>
            <div class="message-bubble assistant" data-testid="chatflow-assistant-message">{{ chatflowAssistantText }}</div>
          </div>
          <div v-else class="workflow-result-card" data-testid="workflow-run-output">
            <div v-for="row in runOutputRows" :key="row.key" class="workflow-result-row">
              <span>{{ row.key }}</span>
              <strong>{{ row.value }}</strong>
            </div>
            <div v-if="runOutputRows.length === 0" class="workflow-result-empty">暂无输出</div>
          </div>
        </section>

        <div class="test-run-actions">
          <el-button :loading="running" type="primary" @click="runCanvasTest">运行</el-button>
        </div>
      </aside>

      <aside v-if="opsPanelOpen" class="ops-panel" data-testid="workflow-ops-panel">
        <div class="config-header">
          <div class="node-type-icon icon-start"><Share /></div>
          <div>
            <h3>发布与运维</h3>
            <span>发布、Open API 与运行观测</span>
          </div>
          <button type="button" aria-label="关闭运维面板" @click="opsPanelOpen = false">×</button>
        </div>

        <div class="ops-tabs" role="tablist" aria-label="workflow operations">
          <button
            type="button"
            :class="{ active: opsActiveTab === 'publish' }"
            @click="opsActiveTab = 'publish'"
          >
            发布
          </button>
          <button
            type="button"
            :class="{ active: opsActiveTab === 'api' }"
            @click="opsActiveTab = 'api'"
          >
            Open API
          </button>
          <button
            type="button"
            :class="{ active: opsActiveTab === 'observe' }"
            @click="opsActiveTab = 'observe'"
          >
            运行观测
          </button>
        </div>

        <section v-if="opsActiveTab === 'publish'" class="config-section">
          <div class="section-title"><span>⌄</span> 发布检查</div>
          <dl class="ops-field-list">
            <div>
              <dt>画布校验</dt>
              <dd>{{ publishValidationErrors.length ? '未通过' : '已通过' }}</dd>
            </div>
            <div>
              <dt>最近试运行</dt>
              <dd>{{ lastTestRunStatus || '未运行' }}</dd>
            </div>
            <div>
              <dt>当前状态</dt>
              <dd>{{ workflowStatus }}</dd>
            </div>
          </dl>
          <ul v-if="publishGate.reasons.length" class="validation-list publish-reasons">
            <li v-for="reason in publishGate.reasons" :key="reason">{{ reason }}</li>
          </ul>
          <div class="publish-actions">
            <el-button
              :disabled="!publishGate.allowed"
              :loading="publishing"
              type="primary"
              @click="publishWorkflow"
            >
              确认发布
            </el-button>
          </div>
        </section>

        <section v-else-if="opsActiveTab === 'api'" class="config-section">
          <div class="section-title"><span>⌄</span> Open API</div>
          <dl class="ops-field-list">
            <div>
              <dt>Method</dt>
              <dd>POST</dd>
            </div>
            <div>
              <dt>Endpoint</dt>
              <dd><code>{{ openApiEndpoint }}</code></dd>
            </div>
          </dl>
          <pre class="ops-code">{{ openApiSample }}</pre>
        </section>

        <section v-else class="config-section">
          <div class="section-title"><span>⌄</span> 运行观测</div>
          <dl class="ops-field-list">
            <div>
              <dt>最近 Run ID</dt>
              <dd>{{ lastTestRunId || '暂无' }}</dd>
            </div>
            <div>
              <dt>最近状态</dt>
              <dd>{{ lastTestRunStatus || '暂无' }}</dd>
            </div>
            <div>
              <dt>输出字段</dt>
              <dd>{{ observeOutputKeys }}</dd>
            </div>
          </dl>
          <pre v-if="lastRunOutput" class="ops-code">{{ JSON.stringify(lastRunOutput, null, 2) }}</pre>
        </section>
      </aside>

      <div v-if="paletteOpen" class="node-palette">
        <button v-for="type in addableNodeTypes" :key="type" type="button" @click="addNode(type)">
          <span class="palette-icon" :class="`icon-${type.toLowerCase()}`">
            <component :is="nodeIcon(type)" />
          </span>
          <span>{{ nodeTypeLabel(type) }}</span>
        </button>
      </div>

      <div class="canvas-toolbar">
        <button type="button" aria-label="缩小">
          <el-icon><Minus /></el-icon>
        </button>
        <span>100%</span>
        <button type="button" aria-label="适应画布">
          <el-icon><FullScreen /></el-icon>
        </button>
        <button type="button" aria-label="自动布局" title="自动布局" @click="autoLayoutCanvas">
          <el-icon><Rank /></el-icon>
        </button>
        <button class="toolbar-add-node" type="button" aria-label="添加节点" @click="paletteOpen = !paletteOpen">
          <el-icon><Plus /></el-icon>
          <span>添加节点</span>
        </button>
      </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  Connection,
  Cpu,
  DataAnalysis,
  Finished,
  FullScreen,
  Minus,
  Operation,
  Plus,
  Rank,
  Share,
} from '@element-plus/icons-vue'
import { Handle, MarkerType, Position, VueFlow, type Edge, type Node } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

import {
  createChatflow,
  createWorkflow,
  getChatflow,
  getWorkflow,
  runChatflow,
  runWorkflow,
  updateChatflow,
  updateWorkflow,
  type WorkflowDetail,
} from '@/api/workflow'
import { buildChatflowRunInput } from './chatflowRunProfile'
import { buildChatflowVariableScopes, insertChatflowVariableReference, type ChatflowVariableScope } from './chatflowVariables'
import { buildChatflowOpenShell, evaluateChatflowPublishGate } from './chatflowPublish'
import {
  addWorkflowNode,
  autoLayoutWorkflowGraph,
  connectWorkflowNodes,
  createDefaultChatflowGraph,
  createDefaultWorkflowGraph,
  deleteWorkflowNode,
  hydrateWorkflowGraph,
  moveWorkflowNode,
  serializeWorkflowGraph,
  type WorkflowCanvasGraph,
  type WorkflowCanvasNodeType,
} from './flowGraph'
import { applyNodeConfigPatch, getNodeConfigSchema } from './nodeConfig'
import { buildVariableCatalog } from './variableCatalog'
import { evaluateWorkflowPublishGate } from './workflowPublish'
import { validateWorkflowGraph } from './workflowValidation'

type OpsTab = 'publish' | 'api' | 'observe'
type CanvasTab = 'compose' | 'stats' | 'open'
type ChatflowScopeState = ChatflowVariableScope & { open: boolean }
const START_VARIABLE_LINE_BUDGET = 350
const START_VARIABLE_BADGE_BASE_WIDTH = 24
const START_VARIABLE_CHAR_WIDTH = 7.2
const START_VARIABLE_GAP = 8
const START_VARIABLE_MORE_WIDTH = 38

const route = useRoute()
const router = useRouter()
const isChatflowMode = computed(() => route.path.startsWith('/chatflows'))
const flowId = computed(() => Number(route.params.id || 0))
const workflowId = flowId
const isEditing = computed(() => flowId.value > 0)
const listPath = computed(() => isChatflowMode.value ? '/chatflows' : '/workflows')

const graph = ref<WorkflowCanvasGraph>(createDefaultGraph())
const form = ref(defaultForm())
const saving = ref(false)
const running = ref(false)
const loading = ref(false)
const canvasTab = ref<CanvasTab>('compose')
const canvasStageRef = ref<HTMLElement | null>(null)
const selectedNodeKey = ref('')
const paletteOpen = ref(false)
const resourcePanelCollapsed = ref(false)
const activeVariableField = ref('')
const variableSearch = ref('')
const lastSavedAt = ref('')
const testPanelOpen = ref(false)
const testInput = ref('hello')
const testResult = ref<Record<string, any> | null>(null)
const validationErrors = ref<string[]>([])
const opsPanelOpen = ref(false)
const opsActiveTab = ref<OpsTab>('publish')
const publishing = ref(false)
const workflowStatus = ref('DRAFT')
const lastTestRunStatus = ref('')
const lastTestRunId = ref(0)
const lastRunOutput = ref<Record<string, any> | null>(null)
const dirtySinceTestRun = ref(true)
const openingText = ref('你好，我可以帮你处理订单、售后和产品咨询。')
const guideQuestions = ref(['查订单进度', '申请退款', '咨询发票'])
const testProfile = ref({
  conversationId: 'conv-demo',
  userId: 'user-demo',
  channel: 'web',
  round: 1,
})
const chatflowVariableScopes = ref<ChatflowScopeState[]>(
  buildChatflowVariableScopes().map((scope, index) => ({ ...scope, open: index === 0 })),
)

const addableNodeTypes: Exclude<WorkflowCanvasNodeType, 'START' | 'END'>[] = ['LLM', 'CONDITION', 'KNOWLEDGE', 'API_CALL']

const icons = {
  START: markRaw(Connection),
  LLM: markRaw(Cpu),
  CONDITION: markRaw(Operation),
  KNOWLEDGE: markRaw(DataAnalysis),
  API_CALL: markRaw(Share),
  END: markRaw(Finished),
}

function createDefaultGraph() {
  return isChatflowMode.value ? createDefaultChatflowGraph() : createDefaultWorkflowGraph()
}

function defaultForm() {
  return isChatflowMode.value
    ? { name: '', description: '通过画布创建的 Chatflow' }
    : { name: '', description: '通过画布创建的工作流' }
}

const saveState = computed(() => {
  if (loading.value) return '正在载入...'
  return lastSavedAt.value ? `已保存 ${lastSavedAt.value}` : '已自动保存草稿'
})

const selectedNode = computed(() => graph.value.nodes.find((node) => node.nodeKey === selectedNodeKey.value))
const selectedSchema = computed(() => selectedNode.value ? getNodeConfigSchema(selectedNode.value.type) : null)
const variableGroups = computed(() => selectedNode.value ? buildVariableCatalog(graph.value, selectedNode.value.nodeKey) : [])
const publishValidationErrors = computed(() => validateWorkflowGraph(graph.value).errors)
const publishGate = computed(() =>
  isChatflowMode.value
    ? evaluateChatflowPublishGate({
      lastRunStatus: lastTestRunStatus.value,
      dirtySinceTestRun: dirtySinceTestRun.value,
    })
    : evaluateWorkflowPublishGate({
      validationErrors: publishValidationErrors.value,
      lastTestRunStatus: lastTestRunStatus.value,
      dirtySinceTestRun: dirtySinceTestRun.value,
    }),
)
const openApiEndpoint = computed(() =>
  isChatflowMode.value
    ? buildChatflowOpenShell({ chatflowId: workflowId.value, channel: testProfile.value.channel }).endpoint
    : `/api/v1/workflows/${workflowId.value || '{workflowId}'}/runs`,
)
const openApiSample = computed(() => JSON.stringify({
  input: isChatflowMode.value
    ? buildChatflowRunInput({ message: testInput.value, ...testProfile.value })
    : {
      userMessage: testInput.value,
      USER_INPUT: testInput.value,
    },
}, null, 2))
const observeOutputKeys = computed(() => {
  if (!lastRunOutput.value) return '暂无'
  const keys = Object.keys(lastRunOutput.value)
  return keys.length ? keys.join(', ') : '无输出'
})
const chatflowAssistantText = computed(() => {
  const output = testResult.value?.output || {}
  return String(output.output ?? output.answer ?? JSON.stringify(output))
})
const chatflowOpeningText = computed(() => isChatflowMode.value ? openingText.value.trim() : '')
const activeGuideQuestions = computed(() => guideQuestions.value.map((item) => item.trim()).filter(Boolean))
const runOutputRows = computed(() => {
  const output = testResult.value?.output || {}
  return Object.entries(output).map(([key, value]) => ({
    key,
    value: formatRunOutputValue(value),
  }))
})
const filteredVariableGroups = computed(() => {
  const keyword = variableSearch.value.trim().toLowerCase()
  if (!keyword) return variableGroups.value
  return variableGroups.value
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        `${item.label} ${item.reference}`.toLowerCase().includes(keyword),
      ),
    }))
    .filter((group) => group.items.length > 0)
})

const flowNodes = computed<Node[]>({
  get() {
    return graph.value.nodes.map((node) => ({
      id: node.nodeKey,
      type: 'coze',
      position: node.position,
      data: {
        nodeKey: node.nodeKey,
        type: node.type,
        name: node.name,
        outputVariable: node.config.outputVariable,
        outputVariables: Array.isArray(node.config.outputVariables) ? node.config.outputVariables.map(String) : [],
      },
      draggable: true,
    }))
  },
  set(nextNodes) {
    const nodePositions = new Map(nextNodes.map((node) => [node.id, node.position]))
    graph.value = {
      ...graph.value,
      nodes: graph.value.nodes.map((node) => {
        const position = nodePositions.get(node.nodeKey)
        return position ? { ...node, position } : node
      }),
    }
    markGraphDirty()
  },
})

const flowEdges = computed<Edge[]>({
  get() {
    return graph.value.edges.map((edge) => ({
      id: edge.id,
      source: edge.sourceNodeKey,
      target: edge.targetNodeKey,
      markerEnd: MarkerType.ArrowClosed,
      style: { stroke: '#5a5cf6', strokeWidth: 2 },
    }))
  },
  set(nextEdges) {
    const currentConditions = new Map(
      graph.value.edges.map((edge) => [edge.id, edge.condition]),
    )
    graph.value = {
      ...graph.value,
      edges: nextEdges.map((edge) => ({
        id: edge.id,
        sourceNodeKey: edge.source,
        targetNodeKey: edge.target,
        condition: currentConditions.has(edge.id) ? currentConditions.get(edge.id) ?? null : null,
      })),
    }
    markGraphDirty()
  },
})

function nodeIcon(type: WorkflowCanvasNodeType) {
  return icons[type]
}

function nodeTypeLabel(type: WorkflowCanvasNodeType) {
  return { START: '开始', LLM: '大模型', CONDITION: '条件', KNOWLEDGE: '知识库', API_CALL: 'API 调用', END: '结束' }[type]
}

function outputBadge(type: WorkflowCanvasNodeType, configured?: string) {
  if (configured) return `str.${configured}`
  if (type === 'CONDITION') return 'str.route'
  return 'str.output'
}

function startVariableTooltip(values: string[]) {
  if (!values.length) return '无输出变量'
  return values.map((value) => `str.${value}`).join(' · ')
}

function estimateStartVariableBadgeWidth(value: string) {
  return Math.min(170, Math.ceil(`str.${value}`.length * START_VARIABLE_CHAR_WIDTH + START_VARIABLE_BADGE_BASE_WIDTH))
}

function startVisibleVariables(values: string[]) {
  const visible: string[] = []
  let usedWidth = 0
  for (let index = 0; index < values.length; index += 1) {
    const width = estimateStartVariableBadgeWidth(values[index])
    const nextWidth = usedWidth + (visible.length ? START_VARIABLE_GAP : 0) + width
    const hiddenAfterThis = values.length - index - 1
    const reserveMoreWidth = hiddenAfterThis > 0
      ? START_VARIABLE_GAP + START_VARIABLE_MORE_WIDTH
      : 0
    if (visible.length > 0 && nextWidth + reserveMoreWidth > START_VARIABLE_LINE_BUDGET) break
    visible.push(values[index])
    usedWidth = nextWidth
  }
  return visible
}

function startHasHiddenVariables(values: string[]) {
  return startVisibleVariables(values).length < values.length
}

function formatRunOutputValue(value: unknown) {
  if (value === null || value === undefined) return '空'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

function addNode(type: Exclude<WorkflowCanvasNodeType, 'START' | 'END'>) {
  const offset = graph.value.nodes.length * 32
  graph.value = addWorkflowNode(graph.value, type, { x: 360 + offset, y: 260 + offset })
  paletteOpen.value = false
  markGraphDirty()
}

function removeNode(nodeKey: string) {
  graph.value = deleteWorkflowNode(graph.value, nodeKey)
  if (selectedNodeKey.value === nodeKey) selectedNodeKey.value = ''
  markGraphDirty()
}

function canKeyboardDeleteNode() {
  return Boolean(selectedNode.value && selectedNode.value.type !== 'START' && selectedNode.value.type !== 'END')
}

function isEditableTarget(target: EventTarget | null) {
  const element = target instanceof HTMLElement ? target : null
  if (!element) return false
  return Boolean(element.closest('input, textarea, select, [contenteditable="true"], .el-input, .el-textarea'))
}

function handleCanvasKeydown(event: KeyboardEvent) {
  if (!['Backspace', 'Delete', 'Enter'].includes(event.key)) return
  if (isEditableTarget(event.target) || !canKeyboardDeleteNode()) return
  event.preventDefault()
  removeNode(selectedNode.value!.nodeKey)
}

function handleConnect(connection: any) {
  graph.value = connectWorkflowNodes(graph.value, connection.source, connection.target)
  markGraphDirty()
}

function handleNodeDragStop(event: any) {
  if (!event?.node?.id || !event.node.position) return
  graph.value = moveWorkflowNode(graph.value, event.node.id, event.node.position)
  markGraphDirty()
}

function handleNodeClick(event: any) {
  selectedNodeKey.value = event?.node?.id || ''
  activeVariableField.value = ''
  variableSearch.value = ''
  void nextTick(() => canvasStageRef.value?.focus())
}

function updateSelectedNode(patch: { name?: string; config?: Record<string, any> }) {
  if (!selectedNode.value) return
  graph.value = {
    ...graph.value,
    nodes: graph.value.nodes.map((node) =>
      node.nodeKey === selectedNode.value?.nodeKey ? applyNodeConfigPatch(node, patch) : node,
    ),
  }
  markGraphDirty()
}

function fieldValue(key: string) {
  if (!selectedNode.value) return ''
  if (key === 'name') return selectedNode.value.name
  return selectedNode.value.config[key] as any
}

function setFieldValue(key: string, value: string | number | null | undefined) {
  if (!selectedNode.value) return
  if (key === 'name') {
    updateSelectedNode({ name: String(value || '') })
    return
  }
  updateSelectedNode({ config: { [key]: value ?? '' } })
}

function canUseVariable(key: string) {
  return ['prompt', 'expression', 'endpoint', 'output'].includes(key)
}

function insertVariable(key: string, reference: string) {
  const currentValue = String(fieldValue(key) || '')
  const nextValue = currentValue ? `${currentValue} ${reference}` : reference
  setFieldValue(key, nextValue)
  activeVariableField.value = ''
  variableSearch.value = ''
}

function insertChatflowVariable(reference: string) {
  const endNode = graph.value.nodes.find((node) => node.nodeKey === 'end')
  const currentValue = String(endNode?.config.output || '')
  const nextValue = insertChatflowVariableReference(currentValue, reference)
  graph.value = {
    ...graph.value,
    nodes: graph.value.nodes.map((node) =>
      node.nodeKey === 'end'
        ? { ...node, config: { ...node.config, outputVariable: 'output', output: nextValue } }
        : node,
    ),
  }
  selectedNodeKey.value = 'end'
  markGraphDirty()
}

function addGuideQuestion() {
  guideQuestions.value = [...guideQuestions.value, '']
  markGraphDirty()
}

function removeGuideQuestion(index: number) {
  guideQuestions.value = guideQuestions.value.filter((_item, itemIndex) => itemIndex !== index)
  markGraphDirty()
}

function applyGuideQuestion(question: string) {
  testInput.value = question
}

function resetChatflowConversationSettings() {
  openingText.value = '你好，我可以帮你处理订单、售后和产品咨询。'
  guideQuestions.value = ['查订单进度', '申请退款', '咨询发票']
}

function syncChatflowSettingsFromGraph() {
  if (!isChatflowMode.value) return
  const startConfig = graph.value.nodes.find((node) => node.nodeKey === 'start')?.config || {}
  openingText.value = String(startConfig.openingText || '你好，我可以帮你处理订单、售后和产品咨询。')
  guideQuestions.value = Array.isArray(startConfig.guideQuestions)
    ? startConfig.guideQuestions.map(String)
    : ['查订单进度', '申请退款', '咨询发票']
}

function graphForPersistence() {
  if (!isChatflowMode.value) return graph.value
  return {
    ...graph.value,
    nodes: graph.value.nodes.map((node) =>
      node.nodeKey === 'start'
        ? {
          ...node,
          config: {
            ...node.config,
            openingText: openingText.value,
            guideQuestions: guideQuestions.value.map((item) => item.trim()).filter(Boolean),
          },
        }
        : node,
    ),
  }
}

function readonlyValues(key: string) {
  if (!selectedNode.value) return []
  const value = selectedNode.value.config[key]
  if (Array.isArray(value)) return value.map(String)
  return value ? [String(value)] : []
}

function autoLayoutCanvas() {
  graph.value = autoLayoutWorkflowGraph(graph.value)
  markGraphDirty()
}

async function loadWorkflow() {
  if (!isEditing.value) {
    graph.value = createDefaultGraph()
    form.value = defaultForm()
    resetChatflowConversationSettings()
    workflowStatus.value = 'DRAFT'
    lastSavedAt.value = ''
    dirtySinceTestRun.value = true
    return
  }
  loading.value = true
  try {
    const detail = (await (isChatflowMode.value ? getChatflow(workflowId.value) : getWorkflow(workflowId.value))) as WorkflowDetail
    form.value = { name: detail.name, description: detail.description || '' }
    workflowStatus.value = detail.status
    graph.value = hydrateWorkflowGraph(detail.nodes, detail.edges)
    syncChatflowSettingsFromGraph()
    lastSavedAt.value = formatClock(new Date(detail.updatedAt))
    dirtySinceTestRun.value = true
  } finally {
    loading.value = false
  }
}

async function saveCanvas() {
  if (!form.value.name.trim()) {
    ElMessage.warning(isChatflowMode.value ? '请输入 Chatflow 名称' : '请输入工作流名称')
    return
  }
  const payload = serializeWorkflowGraph(graphForPersistence())
  saving.value = true
  try {
    if (isEditing.value) {
      const update = isChatflowMode.value ? updateChatflow : updateWorkflow
      await update(workflowId.value, {
        name: form.value.name,
        description: form.value.description,
        nodes: payload.nodes,
        edges: payload.edges,
      })
      ElMessage.success('画布已保存')
      lastSavedAt.value = formatClock(new Date())
      return workflowId.value
    } else {
      const create = isChatflowMode.value ? createChatflow : createWorkflow
      const created = await create({
        name: form.value.name,
        description: form.value.description,
        nodes: payload.nodes,
        edges: payload.edges,
      }) as WorkflowDetail
      ElMessage.success(isChatflowMode.value ? 'Chatflow 创建成功' : '工作流创建成功')
      await router.replace(`${listPath.value}/${created.id}/canvas`)
      lastSavedAt.value = formatClock(new Date())
      return created.id
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
    return 0
  } finally {
    saving.value = false
  }
}

function openTestPanel() {
  testPanelOpen.value = true
  opsPanelOpen.value = false
  selectedNodeKey.value = ''
  testResult.value = null
  validationErrors.value = validateWorkflowGraph(graph.value).errors
}

function openOpsPanel(tab: OpsTab) {
  canvasTab.value = tab === 'api' ? 'open' : tab === 'observe' ? 'stats' : 'compose'
  opsActiveTab.value = tab
  opsPanelOpen.value = true
  testPanelOpen.value = false
  selectedNodeKey.value = ''
}

async function runCanvasTest() {
  const validation = validateWorkflowGraph(graph.value)
  validationErrors.value = validation.errors
  testResult.value = null
  if (!validation.valid) return

  const id = isEditing.value ? await saveCanvas() : await saveCanvas()
  if (!id) return

  running.value = true
  try {
    const result = await (isChatflowMode.value
      ? runChatflow(id, buildChatflowRunInput({ message: testInput.value, ...testProfile.value }))
      : runWorkflow(id, {
        userMessage: testInput.value,
        USER_INPUT: testInput.value,
      })) as any
    testResult.value = result
    lastTestRunStatus.value = String(result?.status || '')
    lastTestRunId.value = Number(result?.runId || 0)
    lastRunOutput.value = result?.output || null
    dirtySinceTestRun.value = false
  } catch (e: any) {
    lastTestRunStatus.value = 'FAILED'
    validationErrors.value = [e?.message || '运行失败']
  } finally {
    running.value = false
  }
}

async function publishWorkflow() {
  if (!publishGate.value.allowed) {
    ElMessage.warning(publishGate.value.reasons[0] || '发布检查未通过')
    return
  }

  const id = await saveCanvas()
  if (!id) return

  publishing.value = true
  try {
    const update = isChatflowMode.value ? updateChatflow : updateWorkflow
    await update(id, { status: 'PUBLISHED' })
    workflowStatus.value = 'PUBLISHED'
    ElMessage.success(isChatflowMode.value ? 'Chatflow 已发布' : '工作流已发布')
  } catch (e: any) {
    ElMessage.error(e?.message || '发布失败')
  } finally {
    publishing.value = false
  }
}

function markGraphDirty() {
  dirtySinceTestRun.value = true
  lastTestRunStatus.value = ''
  lastTestRunId.value = 0
  lastRunOutput.value = null
}

function formatClock(value: Date) {
  return `${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}:${String(value.getSeconds()).padStart(2, '0')}`
}

watch(() => [route.path, route.params.id], loadWorkflow)
onMounted(loadWorkflow)
</script>

<style scoped>
.workflow-canvas-page {
  height: 100vh;
  min-height: 720px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f6f7fb;
}

.canvas-topbar {
  height: 74px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  border-bottom: 1px solid #dfe3ee;
  background: #fff;
  box-shadow: 0 1px 0 rgba(34, 41, 63, 0.04);
}

.canvas-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.back-button {
  width: 28px;
  padding: 0;
  color: #445067;
}

.flow-icon,
.node-type-icon,
.palette-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.flow-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #06b6b6;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-input {
  width: 220px;
}

.title-input :deep(.el-input__wrapper) {
  box-shadow: none;
  padding: 0;
  background: transparent;
}

.title-input :deep(.el-input__inner) {
  height: 30px;
  font-size: 20px;
  font-weight: 700;
  color: #22273a;
}

.flow-info {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #9aa3b5;
  border-radius: 50%;
  font-size: 12px;
  color: #596273;
}

.save-state {
  width: fit-content;
  margin-top: 2px;
  padding: 2px 8px;
  border-radius: 5px;
  background: #eef0f8;
  font-size: 12px;
  color: #616a7f;
}

.canvas-mode-tabs {
  height: 38px;
  display: inline-grid;
  grid-template-columns: repeat(3, minmax(74px, 1fr));
  align-items: center;
  padding: 3px;
  border: 1px solid #e1e5ef;
  border-radius: 9px;
  background: #f6f7fb;
}

.canvas-mode-tabs button {
  height: 30px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #6a7284;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.canvas-mode-tabs button.active {
  background: #fff;
  color: #3339d8;
  box-shadow: 0 2px 8px rgba(44, 51, 84, 0.08);
}

.canvas-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.canvas-workbench {
  position: relative;
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 252px minmax(0, 1fr);
  overflow: hidden;
  background: #f8f9fc;
  transition: grid-template-columns 0.18s ease;
}

.canvas-workbench.resource-collapsed {
  grid-template-columns: 0 minmax(0, 1fr);
}

.resource-panel-toggle {
  position: absolute;
  top: 18px;
  left: 252px;
  z-index: 12;
  width: 28px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dfe3ee;
  border-left: 0;
  border-radius: 0 9px 9px 0;
  background: #fff;
  color: #596273;
  box-shadow: 6px 8px 20px rgba(34, 41, 63, 0.1);
  cursor: pointer;
  opacity: 0.52;
  transition: opacity 0.16s ease, left 0.18s ease, background 0.16s ease;
}

.resource-panel-toggle:hover,
.resource-panel-toggle:focus-visible {
  background: #f7f8fc;
  opacity: 1;
}

.canvas-workbench.resource-collapsed .resource-panel-toggle {
  left: 0;
}

.canvas-resource-panel {
  min-height: 0;
  padding: 16px 12px;
  border-right: 1px solid #dfe3ee;
  overflow-y: auto;
  background: #fff;
}

.resource-header {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 4px 12px;
  border-bottom: 1px solid #edf0f6;
}

.resource-header strong {
  color: #252b3d;
  font-size: 15px;
}

.resource-header span {
  color: #8b94a8;
  font-size: 12px;
}

.resource-section {
  padding: 14px 4px 0;
}

.resource-section h4 {
  margin: 0 0 8px;
  color: #70798d;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.question-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 28px;
  gap: 6px;
  margin-bottom: 6px;
}

.question-row input {
  min-width: 0;
  height: 30px;
  padding: 0 8px;
  border: 1px solid #dfe3ee;
  border-radius: 7px;
  outline: none;
  color: #30364a;
}

.question-row button,
.resource-action {
  border: 1px solid #dfe3ee;
  border-radius: 7px;
  background: #f7f8fc;
  color: #5f687a;
  cursor: pointer;
}

.resource-action {
  width: 100%;
  height: 32px;
  font-weight: 700;
}

.resource-group {
  margin-bottom: 8px;
}

.resource-group > button,
.resource-items button {
  width: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 10px;
  border: 1px solid #e1e5ef;
  border-radius: 8px;
  background: #fff;
  color: #30364a;
  cursor: pointer;
}

.resource-group > button {
  flex-direction: column;
}

.resource-group small,
.resource-items code {
  color: #8b94a8;
  font-size: 11px;
}

.resource-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 6px;
}

.resource-items button {
  flex-direction: column;
}

.resource-items button:hover,
.resource-group > button:hover {
  border-color: #cdd3f7;
  background: #f5f6ff;
}

.resource-stats {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  margin: 0;
}

.resource-stats div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 34px;
  padding: 0 10px;
  border: 1px solid #e1e5ef;
  border-radius: 8px;
  background: #f8f9fc;
}

.resource-stats dt {
  color: #70798d;
  font-size: 12px;
  font-weight: 700;
}

.resource-stats dd {
  margin: 0;
  color: #30364a;
  font-size: 13px;
  font-weight: 800;
}

.selected-node-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  border: 1px solid #e1e5ef;
  border-radius: 8px;
  background: #fff;
}

.selected-node-summary strong {
  color: #30364a;
  font-size: 13px;
}

.selected-node-summary span {
  color: #8b94a8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

.canvas-stage-shell {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.canvas-stage-shell:focus {
  outline: none;
}

.coze-flow {
  width: 100%;
  height: 100%;
  background-color: #f8f9fc;
  background-image: radial-gradient(#bac0ce 1.2px, transparent 1.2px);
  background-size: 24px 24px;
}

.coze-flow :deep(.vue-flow__node) {
  width: auto;
}

.coze-flow :deep(.vue-flow__edge-path) {
  stroke: #5a5cf6;
  stroke-width: 2;
}

.coze-node {
  position: relative;
  width: 420px;
  min-height: 104px;
  padding: 18px;
  border: 1px solid #d9deec;
  border-radius: 10px;
  background: linear-gradient(180deg, #fff, #fbfcff);
  box-shadow: 0 10px 28px rgba(36, 45, 67, 0.08);
  color: #30364a;
  cursor: grab;
  user-select: none;
}

.coze-node.node-start {
  height: 120px;
  overflow: visible;
}

.coze-node:active {
  cursor: grabbing;
}

.coze-node.selected {
  border-color: #6667f6;
  box-shadow: 0 0 0 2px rgba(102, 103, 246, 0.18), 0 10px 28px rgba(36, 45, 67, 0.08);
}

.node-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.node-type-icon {
  width: 32px;
  height: 32px;
  border-radius: 7px;
}

.icon-start,
.icon-end,
.icon-llm {
  background: #5d5ff6;
}

.icon-condition {
  background: #ff9d1b;
}

.icon-knowledge {
  background: #e95085;
}

.icon-api_call {
  background: #12b5b0;
}

.node-title {
  flex: 1;
  overflow: hidden;
  font-size: 20px;
  font-weight: 700;
  line-height: 32px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-line {
  display: flex;
  align-items: center;
  min-width: 0;
  min-height: 30px;
  gap: 8px;
  overflow: hidden;
  color: #9aa2b4;
  font-size: 15px;
  font-weight: 600;
}

.node-variable-list {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
  white-space: nowrap;
}

.node-line em,
.node-variable-badge {
  max-width: 170px;
  overflow: hidden;
  padding: 4px 8px;
  border-radius: 6px;
  background: #eef1f7;
  color: #3e4558;
  font-style: normal;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-variable-badge {
  flex: 0 1 auto;
}

.node-variable-more {
  flex: 0 0 auto;
  padding: 4px 8px;
  border-radius: 6px;
  background: #eef1f7;
  color: #3e4558;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.4;
}

.node-line em.orange {
  background: #fff0e4;
  color: #f57b16;
}

.node-line strong {
  color: #b4bac8;
  font-weight: 500;
}

.node-port {
  width: 12px;
  height: 12px;
  border: 2px solid #fff;
  background: #6b6ff7;
}

.source-port {
  right: -7px;
}

.target-port {
  left: -7px;
}

.node-palette {
  position: absolute;
  left: 50%;
  bottom: 72px;
  z-index: 10;
  width: 220px;
  padding: 10px;
  border: 1px solid #dfe3ee;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 16px 40px rgba(34, 41, 63, 0.16);
  transform: translateX(-50%);
}

.node-config-panel {
  position: absolute;
  top: 18px;
  right: 18px;
  bottom: 76px;
  z-index: 8;
  width: 360px;
  display: flex;
  flex-direction: column;
  border: 1px solid #dfe3ee;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 16px 44px rgba(34, 41, 63, 0.16);
  overflow: hidden;
}

.test-run-panel,
.ops-panel {
  position: absolute;
  top: 18px;
  right: 18px;
  bottom: 76px;
  z-index: 9;
  width: 360px;
  display: flex;
  flex-direction: column;
  border: 1px solid #dfe3ee;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 16px 44px rgba(34, 41, 63, 0.16);
  overflow: hidden;
}

.config-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid #edf0f6;
}

.config-header h3 {
  margin: 0;
  font-size: 17px;
  line-height: 1.3;
  color: #252b3d;
}

.config-header span {
  font-size: 12px;
  color: #8b94a8;
}

.config-header button {
  width: 28px;
  height: 28px;
  margin-left: auto;
  border: 0;
  border-radius: 7px;
  background: #f1f3f8;
  color: #687287;
  font-size: 18px;
  cursor: pointer;
}

.config-section {
  padding: 14px 16px;
  border-bottom: 1px solid #edf0f6;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 700;
  color: #31384c;
}

.section-title span {
  color: #6f778a;
}

.config-field {
  margin-bottom: 12px;
}

.config-field:last-child {
  margin-bottom: 0;
}

.field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.config-field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #828b9f;
}

.variable-trigger {
  height: 24px;
  padding: 0 8px;
  border: 1px solid #dfe3ee;
  border-radius: 6px;
  background: #f7f8fc;
  color: #5b5ef6;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.variable-popover {
  margin-top: 8px;
  padding: 10px;
  border: 1px solid #dfe3ee;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(34, 41, 63, 0.12);
}

.variable-group {
  margin-top: 10px;
}

.variable-group-title {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #7b8498;
}

.variable-group button {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  padding: 8px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #30364a;
  cursor: pointer;
}

.variable-group button:hover {
  background: #f4f6fb;
}

.variable-group code {
  color: #5b5ef6;
  font-size: 12px;
}

.readonly-values {
  min-height: 32px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid #dfe3ee;
  border-radius: 8px;
  background: #f7f8fc;
}

.node-config-panel :deep(.el-input__wrapper),
.node-config-panel :deep(.el-textarea__inner),
.node-config-panel :deep(.el-select__wrapper),
.test-run-panel :deep(.el-textarea__inner) {
  border-radius: 8px;
}

.validation-title {
  color: #d94848;
}

.validation-list {
  margin: 0;
  padding-left: 18px;
  color: #c23b3b;
  font-size: 13px;
  line-height: 1.8;
}

.run-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  color: #6b7487;
  font-size: 12px;
  font-weight: 700;
}

.run-status {
  min-width: 78px;
  padding: 3px 8px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b42318;
  font-size: 11px;
  font-weight: 900;
  line-height: 1.3;
  text-align: center;
}

.run-status.success {
  background: #dcfce7;
  color: #167a3a;
}

.workflow-result-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.workflow-result-row {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 10px;
  padding: 10px;
  border: 1px solid #e1e5ef;
  border-radius: 9px;
  background: #f8f9fc;
}

.workflow-result-row span {
  color: #7c8598;
  font-size: 12px;
  font-weight: 800;
}

.workflow-result-row strong {
  color: #252b3d;
  font-size: 13px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.workflow-result-empty {
  padding: 10px;
  border-radius: 9px;
  background: #f8f9fc;
  color: #8b94a8;
  font-size: 13px;
}

.chatflow-profile-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  margin-top: 10px;
}

.run-input-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.run-input-field label {
  color: #6f778a;
  font-size: 12px;
  font-weight: 800;
}

.run-input-field.compact label {
  font-size: 11px;
}

.chatflow-runtime-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #edf0f6;
}

.conversation-result {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}

.message-bubble {
  max-width: 88%;
  padding: 9px 11px;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.message-bubble.user {
  align-self: flex-end;
  background: #eef0ff;
  color: #3438b8;
}

.message-bubble.assistant {
  align-self: flex-start;
  background: #f0f2f7;
  color: #2f3548;
}

.message-bubble.opening {
  background: #eefaf8;
  color: #0b6862;
}

.chatflow-suggested-questions {
  align-self: flex-start;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 0 2px;
}

.chatflow-suggested-title {
  color: #7c8598;
  font-size: 12px;
  font-weight: 800;
}

.chatflow-guide-list {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.chatflow-guide-list button {
  width: fit-content;
  max-width: 100%;
  min-height: 28px;
  padding: 4px 9px;
  border: 1px solid #cdd3f7;
  border-radius: 999px;
  background: #f6f7ff;
  color: #4b50c8;
  font-size: 12px;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
  overflow-wrap: anywhere;
}

.chatflow-guide-list button:hover {
  background: #eef0ff;
}

.test-run-actions {
  margin-top: auto;
  padding: 14px 16px;
  border-top: 1px solid #edf0f6;
  text-align: right;
}

.ops-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  padding: 10px 12px;
  border-bottom: 1px solid #edf0f6;
  background: #fafbff;
}

.ops-tabs button {
  height: 32px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #6b7487;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.ops-tabs button.active {
  background: #eef0ff;
  color: #5d5ff6;
}

.ops-field-list {
  margin: 0;
}

.ops-field-list div {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 9px 0;
  border-bottom: 1px solid #f0f2f7;
}

.ops-field-list dt {
  color: #858ea2;
  font-size: 12px;
  font-weight: 700;
}

.ops-field-list dd {
  margin: 0;
  max-width: 220px;
  overflow-wrap: anywhere;
  color: #2f3548;
  font-size: 13px;
  font-weight: 700;
  text-align: right;
}

.ops-field-list code {
  color: #5d5ff6;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}

.ops-code {
  max-height: 260px;
  margin: 12px 0 0;
  padding: 10px;
  border-radius: 8px;
  overflow: auto;
  background: #171a24;
  color: #d8def0;
  font-size: 12px;
  line-height: 1.6;
}

.publish-reasons {
  margin-top: 12px;
}

.publish-actions {
  margin-top: 16px;
  text-align: right;
}

.node-palette button {
  width: 100%;
  height: 42px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #2d3447;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.node-palette button:hover {
  background: #f3f5fb;
}

.palette-icon {
  width: 26px;
  height: 26px;
  border-radius: 6px;
}

.canvas-toolbar {
  position: absolute;
  left: 50%;
  bottom: 16px;
  z-index: 5;
  height: 44px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid #dfe3ee;
  border-radius: 12px;
  background: #fff;
  color: #2d3447;
  box-shadow: 0 10px 30px rgba(34, 41, 63, 0.12);
  transform: translateX(-50%);
}

.canvas-toolbar button {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #445067;
  cursor: pointer;
}

.canvas-toolbar span {
  padding: 0 8px;
  font-weight: 600;
}

.canvas-toolbar .toolbar-add-node {
  width: auto;
  min-width: 104px;
  gap: 6px;
  padding: 0 12px;
  border-radius: 8px;
  background: #6366f1;
  color: #fff;
}

.canvas-toolbar .toolbar-add-node span {
  padding: 0;
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 980px) {
  .workflow-canvas-page {
    min-height: 640px;
  }

  .canvas-mode-tabs,
  .canvas-actions {
    display: none;
  }

  .canvas-workbench {
    grid-template-columns: 1fr;
  }

  .canvas-resource-panel {
    display: none;
  }

  .resource-panel-toggle {
    display: none;
  }

  .coze-node {
    width: 340px;
  }
}
</style>
