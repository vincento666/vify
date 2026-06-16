<template>
  <main class="customer-assistant" data-testid="customer-assistant-workspace" aria-label="客服助手工作台">
    <header class="workspace-header">
      <div>
        <h1>客服助手</h1>
        <p>客户话术、坐席建议、任务证据和人工确认动作集中处理。</p>
      </div>
      <div class="workspace-meta">
        <a-tag color="processing">
          <CustomerServiceOutlined />
          {{ sessionLabel }}
        </a-tag>
        <a-tag :color="turnStatusColor">{{ turnStatus.label }}</a-tag>
      </div>
    </header>

    <a-alert
      v-if="turnStatus.kind === 'failed'"
      data-testid="customer-assistant-failed-state"
      type="error"
      show-icon
      :message="turnStatus.label"
      :description="turnStatus.detail"
    />
    <a-alert
      v-if="turnStatus.kind === 'replayed'"
      data-testid="customer-assistant-replayed-state"
      type="info"
      show-icon
      message="已复用幂等结果"
      description="当前回复来自相同 idempotencyKey 的历史结果。"
    />

    <section class="demo-story-strip" data-testid="customer-assistant-demo-stories" aria-label="演示故事线">
      <div class="demo-story-heading">
        <span class="panel-heading-title">
          <CustomerServiceOutlined />
          演示故事线
        </span>
        <a-tag v-if="selectedDemoStory" color="blue">
          {{ selectedDemoStory.customerName }} · {{ selectedDemoStory.maskedPhone }}
        </a-tag>
      </div>
      <div class="demo-story-list">
        <a-button
          v-for="story in demoStories"
          :key="story.storyId"
          class="demo-story-button"
          :type="story.storyId === selectedDemoStoryId ? 'primary' : 'default'"
          :loading="demoStoryLoadingId === story.storyId"
          @click="loadDemoStory(story.storyId)"
        >
          <ThunderboltOutlined />
          <span>{{ story.title }}</span>
          <small>{{ story.customerName }} · {{ story.taskCount }} 任务 · {{ story.pendingActionCount }} 待确认</small>
        </a-button>
        <a-button v-if="demoStories.length === 0" class="demo-story-button" disabled :loading="demoStoriesLoading">
          <HistoryOutlined />
          <span>{{ demoStoriesLoading ? '正在加载演示故事' : '暂无演示故事' }}</span>
          <small>{{ demoStoryError || '请先执行 demo seed' }}</small>
        </a-button>
      </div>
    </section>

    <div class="workspace-grid">
      <section class="workspace-panel conversation-panel" data-testid="customer-conversation-lane">
        <div class="panel-heading">
          <span class="panel-heading-title">
            <MessageOutlined />
            客户侧
          </span>
          <a-tag>Transcript</a-tag>
        </div>
        <div class="message-stream customer-stream">
          <div
            v-if="workspace.customerMessages.length === 0"
            class="empty-state"
            data-testid="customer-assistant-empty-state"
          >
            暂无客户输入
          </div>
          <div
            v-for="messageItem in workspace.customerMessages"
            :key="messageItem.id"
            class="lane-message"
            :class="messageItem.role"
          >
            <span class="message-role">{{ messageLabel(messageItem.role) }}</span>
            <p>{{ messageItem.content }}</p>
            <a-tag v-if="messageItem.pending" color="gold">待坐席审核草稿</a-tag>
          </div>
        </div>
        <div class="lane-composer">
          <a-input
            v-model:value="customerInput"
            aria-label="客户侧输入模拟"
            placeholder="输入客户请求或通话摘录"
          />
          <a-button type="primary" :loading="sendingSource === 'customer'" @click="submitCustomerTurn">
            <SendOutlined />
            模拟客户输入
          </a-button>
        </div>
      </section>

      <section class="workspace-panel conversation-panel" data-testid="operator-conversation-lane">
        <div class="panel-heading">
          <span class="panel-heading-title">
            <RobotOutlined />
            坐席侧
          </span>
          <a-tag color="success">Assistant</a-tag>
        </div>
        <div class="message-stream operator-stream">
          <div
            v-if="workspace.operatorMessages.length === 0"
            class="empty-state"
            data-testid="customer-assistant-operator-empty-state"
          >
            暂无坐席建议
          </div>
          <div
            v-for="messageItem in workspace.operatorMessages"
            :key="messageItem.id"
            class="lane-message"
            :class="messageItem.role"
          >
            <span class="message-role">{{ messageLabel(messageItem.role) }}</span>
            <p>{{ messageItem.content }}</p>
          </div>
        </div>
        <div class="lane-composer">
          <a-input
            v-model:value="operatorInput"
            aria-label="坐席侧内部追问"
            placeholder="向客服助手追问内部处置建议"
          />
          <a-button :loading="sendingSource === 'operator'" @click="submitOperatorTurn">
            <ThunderboltOutlined />
            追问助手
          </a-button>
        </div>
      </section>

      <aside class="operator-panels" aria-label="坐席操作面板">
        <section class="workspace-panel compact-panel" data-testid="operator-progress-checklist">
          <div class="panel-heading">
            <span class="panel-heading-title">
              <ThunderboltOutlined />
              运行进度
            </span>
          </div>
          <div class="progress-list">
            <div
              v-for="stage in workspace.progressStages"
              :key="stage.key"
              class="progress-row"
              :class="stage.status"
            >
              <CheckOutlined v-if="stage.status === 'complete'" />
              <ThunderboltOutlined v-else-if="stage.status === 'active'" />
              <HistoryOutlined v-else />
              <span>{{ stage.label }}</span>
            </div>
          </div>
        </section>

        <section class="workspace-panel compact-panel" data-testid="operator-metrics-panel">
          <div class="panel-heading">
            <span class="panel-heading-title">
              <DashboardOutlined />
              观测指标
            </span>
          </div>
          <div v-if="metricsSummary.empty" class="empty-compact">暂无会话指标</div>
          <div class="metrics-grid" aria-label="人工采纳率">
            <div
              v-for="tile in metricsSummary.tiles"
              :key="tile.key"
              class="metric-tile"
              :class="tile.tone"
            >
              <span>{{ tile.label }}</span>
              <strong>{{ tile.value }}</strong>
            </div>
          </div>
          <div v-if="metricsSummary.failures.length" class="failure-list">
            <div v-for="failure in metricsSummary.failures" :key="`${failure.taskId}:${failure.reason}`">
              <a-tag color="error">{{ failure.taskType }}</a-tag>
              <span>{{ failure.source }}</span>
              <p>{{ failure.reason }}</p>
            </div>
          </div>
        </section>

        <section class="workspace-panel compact-panel" data-testid="operator-recognition-evidence-panel">
          <div class="panel-heading">
            <span class="panel-heading-title">
              <ThunderboltOutlined />
              识别证据
            </span>
            <span class="panel-count">{{ workspace.recognitionEvidence.length }}</span>
          </div>
          <div class="recognition-evidence-list">
            <div
              v-if="workspace.recognitionEvidence.length === 0"
              class="empty-compact"
              data-testid="operator-recognition-empty-state"
            >
              暂无任务识别证据
            </div>
            <div
              v-for="recognition in workspace.recognitionEvidence"
              :key="recognition.key"
              class="recognition-evidence-row"
            >
              <div class="recognition-main">
                <strong>{{ recognition.sequenceLabel }} {{ recognition.taskKey }}</strong>
                <span>{{ recognition.taskType }} · {{ recognition.workerRoute }}</span>
              </div>
              <div class="recognition-profile">
                <a-tag color="blue">{{ recognition.profileId }}</a-tag>
                <span>模型 {{ recognition.modelPolicyRef }}</span>
                <span>提示词 {{ recognition.promptRef }}</span>
                <span>风险 {{ recognition.riskPolicyRef }}</span>
                <span v-if="recognition.toolRefs.length">工具 {{ recognition.toolRefs.join('、') }}</span>
              </div>
            </div>
          </div>
        </section>

        <section class="workspace-panel compact-panel" data-testid="operator-task-ledger">
          <div class="panel-heading">
            <span class="panel-heading-title">
              <OrderedListOutlined />
              任务台账
            </span>
            <div class="heading-meta">
              <a-tag v-if="workerProfileError" color="warning">配置未加载</a-tag>
              <a-tag v-else-if="workerProfilesLoading" color="processing">配置加载中</a-tag>
              <span class="panel-count">{{ workspace.taskSummary.items.length }}</span>
            </div>
          </div>
          <div class="task-list">
            <div
              v-if="workspace.taskSummary.items.length === 0"
              class="empty-compact"
              data-testid="operator-task-empty-state"
            >
              暂无任务
            </div>
            <div v-for="task in workspace.taskSummary.items" :key="task.id" class="task-row">
              <div>
                <strong>{{ task.displayName }}</strong>
                <span>
                  {{ task.taskKey }} · {{ task.workerType }}
                  <template v-if="task.workerRef"> · {{ task.workerRef }}</template>
                </span>
              </div>
              <div v-if="task.profile" class="task-profile" data-testid="operator-task-profile">
                <a-tag color="blue">{{ task.profile.profileId }}</a-tag>
                <span>模型 {{ task.profile.modelPolicyRef }}</span>
                <span>提示词 {{ task.profile.promptRef }}</span>
                <span>风险 {{ task.profile.riskPolicyRef }}</span>
                <span v-if="task.profile.toolRefs.length">工具 {{ task.profile.toolRefs.join('、') }}</span>
              </div>
              <a-tag :color="statusColor(task.statusTone)">{{ task.status }}</a-tag>
              <p v-if="task.missingFields.length">缺失：{{ task.missingFields.join('、') }}</p>
              <div
                v-if="task.availableControls.length"
                class="task-controls"
                data-testid="operator-task-controls"
              >
                <a-tooltip
                  v-for="control in task.availableControls"
                  :key="control"
                  :title="taskControlTooltip(control)"
                >
                  <a-button
                    size="small"
                    :danger="control === 'cancel'"
                    :loading="taskControlLoadingKey === `${task.id}:${control}`"
                    @click="proposeTaskControl(task.id, control)"
                  >
                    <CloseOutlined v-if="control === 'cancel'" />
                    <ThunderboltOutlined v-else />
                    <span v-if="control === 'retry'">重试</span>
                    <span v-else-if="control === 'cancel'">取消</span>
                    <span v-else>恢复</span>
                  </a-button>
                </a-tooltip>
              </div>
            </div>
          </div>
        </section>

        <section class="workspace-panel compact-panel" data-testid="operator-recommendation-panel">
          <div class="panel-heading">
            <span class="panel-heading-title">
              <BulbOutlined />
              坐席建议
            </span>
          </div>
          <p class="panel-copy">{{ workspace.recommendation.operatorRecommendation || '暂无坐席建议' }}</p>
        </section>

        <section class="workspace-panel compact-panel" data-testid="operator-advisory-evidence-panel">
          <div class="panel-heading">
            <span class="panel-heading-title">
              <DashboardOutlined />
              追问证据
            </span>
            <span class="panel-count">{{ workspace.operatorAdvisoryEvidence.length }}</span>
          </div>
          <div class="advisory-evidence-list">
            <div
              v-if="workspace.operatorAdvisoryEvidence.length === 0"
              class="empty-compact"
              data-testid="operator-advisory-empty-state"
            >
              暂无坐席追问证据
            </div>
            <div
              v-for="advisory in workspace.operatorAdvisoryEvidence"
              :key="advisory.key"
              class="advisory-evidence-row"
            >
              <div class="advisory-main">
                <strong>{{ advisory.sequenceLabel }} {{ advisory.turnMode }}</strong>
                <span>任务 {{ advisory.taskCount }} · 事件 {{ advisory.eventCount }}</span>
              </div>
              <div class="advisory-metrics">
                <a-tag color="blue">SOP {{ advisory.evidenceCount }}</a-tag>
                <a-tag color="green">知识 {{ advisory.knowledgeSnippetCount }}</a-tag>
              </div>
              <p v-if="advisory.warnings.length">提示：{{ advisory.warnings.join('；') }}</p>
            </div>
          </div>
        </section>

        <section class="workspace-panel compact-panel" data-testid="operator-draft-panel">
          <div class="panel-heading">
            <span class="panel-heading-title">
              <EditOutlined />
              客户回复草稿
            </span>
            <a-tag :color="draftApplied ? 'success' : 'default'">
              {{ draftApplied ? '已本地应用' : '待审核' }}
            </a-tag>
          </div>
          <p class="draft-copy">{{ workspace.recommendation.customerReplyDraft || '暂无客户回复草稿' }}</p>
          <div class="panel-actions">
            <a-tooltip title="复制客户回复草稿">
              <a-button size="small" aria-label="复制客户回复草稿" :disabled="!hasDraft" @click="copyDraft">
                <CopyOutlined />
                复制
              </a-button>
            </a-tooltip>
            <a-tooltip title="本地应用客户回复草稿">
              <a-button
                size="small"
                type="primary"
                aria-label="本地应用客户回复草稿"
                :disabled="!hasDraft"
                @click="applyDraftLocal"
              >
                <CheckOutlined />
                本地应用
              </a-button>
            </a-tooltip>
          </div>
        </section>

        <section class="workspace-panel compact-panel" data-testid="operator-proposed-actions-panel">
          <div class="panel-heading">
            <span class="panel-heading-title">
              <SafetyCertificateOutlined />
              待确认动作
            </span>
            <span class="panel-count">{{ workspace.proposedActions.length }}</span>
          </div>
          <div class="action-list">
            <div
              v-if="workspace.proposedActions.length === 0"
              class="empty-compact"
              data-testid="operator-action-empty-state"
            >
              暂无待确认动作
            </div>
            <div v-for="action in workspace.proposedActions" :key="action.id" class="action-row">
              <div>
                <strong>{{ action.title }}</strong>
                <span>{{ action.actionType }} · #{{ action.id }}</span>
              </div>
              <a-tag v-if="isProposedTaskCommand(action)" color="blue">任务变更</a-tag>
              <a-tag :color="action.status === 'PENDING' ? 'warning' : 'default'">{{ action.status }}</a-tag>
              <code>{{ compactPayload(action.payload) }}</code>
              <div
                v-if="editingActionId === action.id"
                class="action-edit-form"
                data-testid="operator-action-edit-form"
              >
                <a-input
                  v-model:value="editingActionTitle"
                  aria-label="修改拟议动作标题"
                  placeholder="拟议动作标题"
                />
                <a-textarea
                  v-model:value="editingActionPayload"
                  aria-label="修改拟议动作参数"
                  :auto-size="{ minRows: 4, maxRows: 8 }"
                  placeholder="拟议动作参数 JSON"
                />
                <p v-if="editingActionError" class="edit-error">{{ editingActionError }}</p>
                <div class="panel-actions action-edit-actions">
                  <a-button
                    size="small"
                    type="primary"
                    :loading="actionLoadingId === action.id"
                    @click="saveEditedAction(action.id)"
                  >
                    <CheckOutlined />
                    保存修改
                  </a-button>
                  <a-button size="small" @click="cancelEditAction">
                    <CloseOutlined />
                    取消修改
                  </a-button>
                </div>
              </div>
              <div class="panel-actions">
                <a-tooltip title="修改拟议动作">
                  <a-button
                    size="small"
                    aria-label="修改拟议动作"
                    :disabled="action.status !== 'PENDING'"
                    @click="startEditAction(action)"
                  >
                    <EditOutlined />
                    修改
                  </a-button>
                </a-tooltip>
                <a-tooltip :title="actionConfirmTooltip(action)">
                  <a-button
                    size="small"
                    aria-label="确认拟议动作"
                    :disabled="action.status !== 'PENDING'"
                    :loading="actionLoadingId === action.id"
                    @click="confirmAction(action.id)"
                  >
                    <CheckOutlined />
                    {{ actionConfirmLabel(action) }}
                  </a-button>
                </a-tooltip>
                <a-tooltip title="拒绝拟议动作">
                  <a-button
                    size="small"
                    aria-label="拒绝拟议动作"
                    :disabled="action.status !== 'PENDING'"
                    :loading="actionLoadingId === action.id"
                    danger
                    @click="rejectAction(action.id)"
                  >
                    <CloseOutlined />
                    拒绝
                  </a-button>
                </a-tooltip>
                <a-tooltip title="执行已确认动作">
                  <a-button
                    size="small"
                    type="primary"
                    aria-label="执行已确认动作"
                    :disabled="action.status !== 'CONFIRMED' || isProposedTaskCommand(action)"
                    :loading="actionLoadingId === action.id"
                    @click="executeAction(action.id)"
                  >
                    <ThunderboltOutlined />
                    执行动作
                  </a-button>
                </a-tooltip>
              </div>
            </div>
          </div>
        </section>

        <section class="workspace-panel compact-panel" data-testid="operator-event-timeline">
          <div class="panel-heading">
            <span class="panel-heading-title">
              <HistoryOutlined />
              运行事件
            </span>
            <span class="panel-count">{{ workspace.eventTimeline.length }}</span>
          </div>
          <a-collapse v-model:active-key="expandedEventKeys" ghost>
            <a-collapse-panel v-if="workspace.eventTimeline.length === 0" key="empty-events" header="暂无运行事件" disabled />
            <a-collapse-panel
              v-for="event in workspace.eventTimeline"
              :key="event.key"
              :header="`${event.sequenceLabel} ${event.title}`"
            >
              <div class="event-detail">
                <a-tag>{{ event.visibilityLabel }}</a-tag>
                <a-tag>{{ event.sourceLabel }}</a-tag>
                <code>{{ event.payloadPreview }}</code>
              </div>
            </a-collapse-panel>
          </a-collapse>
        </section>

        <section class="workspace-panel compact-panel" data-testid="operator-warnings-panel">
          <div class="panel-heading">
            <span class="panel-heading-title">
              <WarningOutlined />
              风险提示
            </span>
          </div>
          <div
            v-if="workspace.recommendation.warnings.length === 0"
            class="empty-compact"
            data-testid="operator-warning-empty-state"
          >
            暂无风险提示
          </div>
          <a-alert
            v-for="warning in workspace.recommendation.warnings"
            :key="warning"
            type="warning"
            show-icon
            :message="warning"
          />
        </section>
      </aside>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import {
  listCustomerAssistantDemoStories,
  listCustomerAssistantWorkerProfiles,
  type CustomerAssistantDemoStory,
  type CustomerAssistantProposedAction,
  type CustomerAssistantTaskControlType,
  type CustomerAssistantWorkerProfile,
} from '@/api/customerAssistant'
import {
  BulbOutlined,
  CheckOutlined,
  CloseOutlined,
  CopyOutlined,
  CustomerServiceOutlined,
  DashboardOutlined,
  EditOutlined,
  HistoryOutlined,
  MessageOutlined,
  OrderedListOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'

import {
  confirmCustomerAssistantRuntimeAction,
  createCustomerAssistantRuntimeState,
  executeCustomerAssistantRuntimeAction,
  loadCustomerAssistantDemoStory,
  proposeCustomerAssistantRuntimeTaskControl,
  rejectCustomerAssistantRuntimeAction,
  sendCustomerAssistantRuntimeTurn,
  updateCustomerAssistantRuntimeAction,
} from './customerAssistantRuntime'
import {
  buildCustomerAssistantStoryQuery,
  customerAssistantStoryIdFromQuery,
  selectCustomerAssistantDemoStoryToOpen,
} from './customerAssistantStoryLinks'
import {
  applyCustomerAssistantDraftLocally,
  createCustomerAssistantDraftState,
  formatCustomerAssistantMetrics,
  formatCustomerAssistantTurnStatus,
  summarizeCustomerAssistantTasks,
  type CustomerAssistantTaskRow,
} from './customerAssistantViewModel'

const customerInput = ref('我要退票')
const operatorInput = ref('请给我处置建议')
const draftApplied = ref(false)
const sendingSource = ref<'customer' | 'operator' | null>(null)
const actionLoadingId = ref<number | null>(null)
const taskControlLoadingKey = ref<string | null>(null)
const expandedEventKeys = ref<string[]>([])
const runtimeState = ref(createCustomerAssistantRuntimeState())
const demoStories = ref<CustomerAssistantDemoStory[]>([])
const selectedDemoStoryId = ref<string | null>(null)
const demoStoriesLoading = ref(false)
const demoStoryLoadingId = ref<string | null>(null)
const demoStoryError = ref<string | null>(null)
const workerProfiles = ref<CustomerAssistantWorkerProfile[]>([])
const workerProfilesLoading = ref(false)
const workerProfileError = ref<string | null>(null)
const editingActionId = ref<number | null>(null)
const editingActionTitle = ref('')
const editingActionPayload = ref('')
const editingActionError = ref<string | null>(null)
const route = useRoute()
const router = useRouter()

const workspace = computed(() => ({
  ...runtimeState.value,
  taskSummary: summarizeCustomerAssistantTasks(runtimeState.value.tasks, workerProfiles.value),
}))
const metricsSummary = computed(() => formatCustomerAssistantMetrics(workspace.value.metrics))
const selectedDemoStory = computed(() =>
  demoStories.value.find((story) => story.storyId === selectedDemoStoryId.value) ?? null,
)
const sessionLabel = computed(() =>
  workspace.value.sessionId === null ? '尚未创建会话' : `Session #${workspace.value.sessionId}`,
)
const draftState = computed(() =>
  createCustomerAssistantDraftState(workspace.value.recommendation.customerReplyDraft, draftApplied.value),
)
const hasDraft = computed(() => draftState.value.text.trim().length > 0)
const turnStatus = computed(() =>
  formatCustomerAssistantTurnStatus({
    loading: runtimeState.value.loading,
    error: runtimeState.value.error,
    replayed: runtimeState.value.replayed,
  }),
)
const turnStatusColor = computed(() => {
  if (turnStatus.value.kind === 'failed') return 'error'
  if (turnStatus.value.kind === 'loading') return 'processing'
  if (turnStatus.value.kind === 'replayed') return 'blue'
  return 'default'
})

onMounted(() => {
  void loadDemoStories()
  void loadWorkerProfiles()
})

function messageLabel(role: string) {
  if (role === 'customer') return '客户'
  if (role === 'operator') return '坐席'
  if (role === 'draft') return '草稿'
  return '助手'
}

function statusColor(tone: CustomerAssistantTaskRow['statusTone']) {
  const colors: Record<CustomerAssistantTaskRow['statusTone'], string> = {
    default: 'default',
    error: 'error',
    processing: 'processing',
    success: 'success',
    warning: 'warning',
  }
  return colors[tone]
}

function compactPayload(payload: Record<string, unknown>) {
  return JSON.stringify(payload)
}

function isProposedTaskCommand(action: CustomerAssistantProposedAction) {
  return action.actionType === 'PROPOSED_TASK_COMMAND'
}

function actionConfirmLabel(action: CustomerAssistantProposedAction) {
  return isProposedTaskCommand(action) ? '确认任务变更' : '确认动作'
}

function actionConfirmTooltip(action: CustomerAssistantProposedAction) {
  return isProposedTaskCommand(action) ? '确认任务变更' : '确认拟议动作'
}

function startEditAction(action: CustomerAssistantProposedAction) {
  editingActionId.value = action.id
  editingActionTitle.value = action.title
  editingActionPayload.value = JSON.stringify(action.payload, null, 2)
  editingActionError.value = null
}

function cancelEditAction() {
  editingActionId.value = null
  editingActionTitle.value = ''
  editingActionPayload.value = ''
  editingActionError.value = null
}

async function saveEditedAction(actionId: number) {
  editingActionError.value = null
  let payload: Record<string, unknown>
  try {
    payload = JSON.parse(editingActionPayload.value || '{}') as Record<string, unknown>
  } catch {
    editingActionError.value = '动作参数必须是合法 JSON'
    return
  }
  actionLoadingId.value = actionId
  try {
    runtimeState.value = await updateCustomerAssistantRuntimeAction(runtimeState.value, actionId, {
      title: editingActionTitle.value.trim(),
      payload,
    })
    cancelEditAction()
    message.success('已保存动作修改')
  } catch (error) {
    catchCustomerAssistantError(error, '保存动作修改失败')
  } finally {
    actionLoadingId.value = null
  }
}

function taskControlTooltip(control: CustomerAssistantTaskControlType) {
  if (control === 'retry') return '生成重试任务的待确认动作'
  if (control === 'cancel') return '生成取消任务的待确认动作'
  return '生成恢复任务的待确认动作'
}

function taskControlReason(control: CustomerAssistantTaskControlType) {
  if (control === 'retry') return 'operator retry requested from workbench'
  if (control === 'cancel') return 'operator cancel requested from workbench'
  return 'operator resume requested from workbench'
}

async function loadDemoStories() {
  demoStoriesLoading.value = true
  demoStoryError.value = null
  try {
    const result = await listCustomerAssistantDemoStories()
    demoStories.value = result.list
    const storyId = selectCustomerAssistantDemoStoryToOpen(
      result.list,
      customerAssistantStoryIdFromQuery(route.query),
      selectedDemoStoryId.value,
    )
    if (storyId) {
      await loadDemoStory(storyId)
    }
  } catch (error) {
    demoStoryError.value = error instanceof Error ? error.message : '演示故事加载失败'
  } finally {
    demoStoriesLoading.value = false
  }
}

async function loadWorkerProfiles() {
  workerProfilesLoading.value = true
  workerProfileError.value = null
  try {
    const result = await listCustomerAssistantWorkerProfiles()
    workerProfiles.value = result.list
  } catch (error) {
    workerProfileError.value = error instanceof Error ? error.message : '任务配置加载失败'
  } finally {
    workerProfilesLoading.value = false
  }
}

async function loadDemoStory(storyId: string) {
  demoStoryLoadingId.value = storyId
  demoStoryError.value = null
  try {
    runtimeState.value = await loadCustomerAssistantDemoStory(storyId)
    selectedDemoStoryId.value = storyId
    syncSelectedDemoStoryRoute(storyId)
    draftApplied.value = false
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '演示故事加载失败'
    demoStoryError.value = errorMessage
    message.error(errorMessage)
  } finally {
    demoStoryLoadingId.value = null
  }
}

function syncSelectedDemoStoryRoute(storyId: string) {
  if (customerAssistantStoryIdFromQuery(route.query) === storyId) return
  void router
    .replace({ query: buildCustomerAssistantStoryQuery(route.query, storyId) })
    .catch(() => undefined)
}

async function proposeTaskControl(taskId: number, controlType: CustomerAssistantTaskControlType) {
  taskControlLoadingKey.value = `${taskId}:${controlType}`
  try {
    runtimeState.value = await proposeCustomerAssistantRuntimeTaskControl(
      runtimeState.value,
      taskId,
      controlType,
      taskControlReason(controlType),
    )
    message.success('已生成待确认任务控制')
  } catch (error) {
    catchCustomerAssistantError(error, '生成任务控制失败')
  } finally {
    taskControlLoadingKey.value = null
  }
}

async function copyDraft() {
  try {
    await navigator.clipboard?.writeText(draftState.value.text)
    message.success('客户回复草稿已复制到本地上下文')
  } catch {
    message.success('客户回复草稿已复制到本地上下文')
  }
}

function applyDraftLocal() {
  draftApplied.value = applyCustomerAssistantDraftLocally(draftState.value).applied
  message.success('客户回复草稿已本地应用，未外发')
}

async function submitCustomerTurn() {
  await submitTurn('customer', customerInput.value)
}

async function submitOperatorTurn() {
  await submitTurn('operator', operatorInput.value)
}

async function submitTurn(actor: 'customer' | 'operator', text: string) {
  if (!text.trim()) return
  sendingSource.value = actor
  runtimeState.value = {
    ...runtimeState.value,
    loading: true,
    error: null,
  }
  try {
    runtimeState.value = await sendCustomerAssistantRuntimeTurn(
      runtimeState.value,
      {
        message: text.trim(),
        actor,
        idempotencyKey: `customer-assistant-${actor}-${Date.now()}`,
      },
      {},
      {
        onLiveState: (state) => {
          runtimeState.value = state
        },
      },
    )
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : '客服助手调用失败'
    setRuntimeError(errorMessage)
    message.error(errorMessage)
  } finally {
    sendingSource.value = null
  }
}

function setRuntimeError(errorMessage: string) {
  runtimeState.value = {
    ...runtimeState.value,
    loading: false,
    error: errorMessage,
  }
}

function catchCustomerAssistantError(error: unknown, fallbackMessage: string) {
  const errorMessage = error instanceof Error ? error.message : fallbackMessage
  setRuntimeError(errorMessage)
  message.error(errorMessage)
  return errorMessage
}

async function confirmAction(actionId: number) {
  actionLoadingId.value = actionId
  try {
    runtimeState.value = await confirmCustomerAssistantRuntimeAction(runtimeState.value, actionId)
  } catch (error) {
    catchCustomerAssistantError(error, '确认动作失败')
  } finally {
    actionLoadingId.value = null
  }
}

async function rejectAction(actionId: number) {
  actionLoadingId.value = actionId
  try {
    runtimeState.value = await rejectCustomerAssistantRuntimeAction(runtimeState.value, actionId)
  } catch (error) {
    catchCustomerAssistantError(error, '拒绝动作失败')
  } finally {
    actionLoadingId.value = null
  }
}

async function executeAction(actionId: number) {
  actionLoadingId.value = actionId
  try {
    runtimeState.value = await executeCustomerAssistantRuntimeAction(runtimeState.value, actionId)
  } catch (error) {
    catchCustomerAssistantError(error, '执行动作失败')
  } finally {
    actionLoadingId.value = null
  }
}
</script>

<style scoped>
.customer-assistant {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 40rem;
}

.workspace-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.workspace-header h1 {
  margin: 0;
  font-size: 1.5rem;
  line-height: 1.3;
}

.workspace-header p {
  margin: 0.35rem 0 0;
  color: #5c667a;
  font-size: 0.875rem;
}

.workspace-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
}

.demo-story-strip {
  display: grid;
  gap: 0.75rem;
  padding: 0.875rem;
  border: 0.0625rem solid #d9e6f7;
  border-radius: 0.5rem;
  background: #f7fbff;
}

.demo-story-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.demo-story-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.625rem;
}

.demo-story-button {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr);
  gap: 0.25rem 0.5rem;
  align-items: center;
  justify-content: start;
  min-height: 3.8rem;
  height: auto;
  padding: 0.65rem 0.75rem;
  text-align: left;
  white-space: normal;
}

.demo-story-button small {
  grid-column: 2;
  overflow: hidden;
  color: #5c667a;
  font-size: 0.75rem;
  line-height: 1.35;
  text-overflow: ellipsis;
}

.demo-story-button.ant-btn-primary small {
  color: #e7f0ff;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(18rem, 1fr) minmax(20rem, 1.1fr) minmax(22rem, 0.95fr);
  gap: 1rem;
  align-items: start;
}

.workspace-panel {
  border: 0.0625rem solid #dde3ee;
  border-radius: 0.5rem;
  background: #ffffff;
}

.conversation-panel {
  display: flex;
  flex-direction: column;
  min-height: 36rem;
}

.operator-panels {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.compact-panel {
  padding: 0.875rem;
}

.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  min-height: 2rem;
  padding: 0.875rem;
  border-bottom: 0.0625rem solid #edf0f6;
}

.compact-panel > .panel-heading {
  min-height: auto;
  padding: 0 0 0.65rem;
}

.panel-heading-title {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  color: #1d2535;
  font-weight: 600;
}

.heading-meta {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.45rem;
}

.panel-count {
  min-width: 1.5rem;
  border-radius: 999rem;
  background: #eef4ff;
  color: #2456a7;
  font-size: 0.75rem;
  line-height: 1.5rem;
  text-align: center;
}

.message-stream {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.75rem;
  min-height: 23rem;
  max-height: 30rem;
  padding: 0.875rem;
  overflow: auto;
}

.lane-message {
  display: grid;
  gap: 0.45rem;
  padding: 0.75rem;
  border: 0.0625rem solid #e7ebf3;
  border-radius: 0.5rem;
  background: #fbfcff;
}

.lane-message.assistant {
  border-color: #cfe3ff;
  background: #f5f9ff;
}

.lane-message.draft {
  border-color: #ffe2a8;
  background: #fffaf0;
}

.lane-message p {
  margin: 0;
  color: #222b3a;
  font-size: 0.875rem;
  line-height: 1.55;
  white-space: pre-wrap;
}

.message-role {
  color: #647086;
  font-size: 0.75rem;
  font-weight: 600;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 8rem;
  border: 0.0625rem dashed #d7deea;
  border-radius: 0.5rem;
  color: #667085;
  font-size: 0.875rem;
}

.lane-composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.625rem;
  padding: 0.875rem;
  border-top: 0.0625rem solid #edf0f6;
}

.task-list,
.action-list,
.progress-list,
.recognition-evidence-list,
.advisory-evidence-list {
  display: grid;
  gap: 0.625rem;
}

.progress-row {
  display: grid;
  grid-template-columns: 1.25rem minmax(0, 1fr);
  gap: 0.5rem;
  align-items: center;
  min-height: 2rem;
  color: #667085;
  font-size: 0.8125rem;
}

.progress-row svg {
  width: 1rem;
  height: 1rem;
}

.progress-row.active {
  color: #2456a7;
  font-weight: 600;
}

.progress-row.complete {
  color: #16794c;
  font-weight: 600;
}

.task-row,
.action-row,
.recognition-evidence-row,
.advisory-evidence-row {
  display: grid;
  gap: 0.5rem;
  padding: 0.65rem;
  border: 0.0625rem solid #edf0f6;
  border-radius: 0.45rem;
  background: #fbfcff;
}

.task-row > div:first-child,
.action-row > div:first-child,
.recognition-main,
.advisory-main {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.task-row span,
.action-row span,
.recognition-evidence-row span,
.advisory-evidence-row span {
  color: #667085;
  font-size: 0.75rem;
}

.task-row p,
.advisory-evidence-row p {
  margin: 0;
  color: #8a5a00;
  font-size: 0.8125rem;
}

.task-profile {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
  color: #4d5b70;
  font-size: 0.75rem;
  line-height: 1.45;
}

.recognition-profile {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
  color: #4d5b70;
  font-size: 0.75rem;
  line-height: 1.45;
}

.advisory-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.task-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
}

.metric-tile {
  display: grid;
  gap: 0.25rem;
  min-height: 3.1rem;
  padding: 0.55rem;
  border: 0.0625rem solid #e1e7f0;
  border-radius: 0.45rem;
  background: #fbfcff;
}

.metric-tile span {
  color: #667085;
  font-size: 0.75rem;
  line-height: 1.35;
}

.metric-tile strong {
  color: #1d2535;
  font-size: 1.15rem;
  line-height: 1.1;
}

.metric-tile.success {
  border-color: #b7dfc9;
  background: #f4fbf7;
}

.metric-tile.warning {
  border-color: #f3d599;
  background: #fffbf0;
}

.metric-tile.processing {
  border-color: #bad3f7;
  background: #f5f9ff;
}

.failure-list {
  display: grid;
  gap: 0.45rem;
  margin-top: 0.65rem;
}

.failure-list > div {
  display: grid;
  gap: 0.3rem;
  padding: 0.55rem;
  border: 0.0625rem solid #f2c2bc;
  border-radius: 0.45rem;
  background: #fff7f5;
}

.failure-list span,
.failure-list p {
  margin: 0;
  color: #5c667a;
  font-size: 0.75rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.panel-copy,
.draft-copy {
  margin: 0;
  color: #2d3648;
  font-size: 0.875rem;
  line-height: 1.55;
  white-space: pre-wrap;
}

.draft-copy {
  padding: 0.7rem;
  border: 0.0625rem dashed #f0c36d;
  border-radius: 0.45rem;
  background: #fffaf0;
}

.panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.65rem;
}

.action-edit-form {
  display: grid;
  gap: 0.5rem;
  padding: 0.6rem;
  border: 0.0625rem dashed #b8c7dc;
  border-radius: 0.45rem;
  background: #f7fbff;
}

.action-edit-actions {
  margin-top: 0;
}

.edit-error {
  margin: 0;
  color: #b42318;
  font-size: 0.8125rem;
  line-height: 1.45;
}

.action-row code,
.event-detail code {
  display: block;
  padding: 0.45rem;
  border-radius: 0.35rem;
  background: #f3f5f9;
  color: #344054;
  font-size: 0.75rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.event-detail {
  display: grid;
  gap: 0.45rem;
}

@media (max-width: 86rem) {
  .workspace-grid {
    grid-template-columns: minmax(18rem, 1fr) minmax(18rem, 1fr);
  }

  .operator-panels {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(2, minmax(18rem, 1fr));
  }
}

@media (max-width: 58rem) {
  .workspace-header,
  .lane-composer {
    grid-template-columns: 1fr;
  }

  .workspace-grid,
  .operator-panels {
    display: flex;
    flex-direction: column;
  }
}
</style>
