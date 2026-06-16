<template>
  <section class="experiments-panel">
    <template v-if="!stepperVisible">
      <div class="panel-toolbar">
        <a-input
          v-model:value="searchName"
          placeholder="搜索实验" allow-clear
          class="search-input"
          @input="onSearch"
        />
        <a-button type="primary" data-testid="create-experiment" @click="openCreate">
          创建实验
        </a-button>
      </div>

      <div v-if="experiments.length === 0 && !loading" class="empty-panel compact">
        <h3>先跑一次目标实验</h3>
        <p>选择 Agent、Workflow 或 Chatflow、评测集和评估器后运行，报告会展示分数、通过率和失败用例。</p>
        <a-button type="primary" @click="openCreate">创建实验</a-button>
      </div>

      <div v-else class="experiment-grid">
        <article v-for="experiment in experiments" :key="experiment.id" class="experiment-card">
          <div>
            <div class="card-title-row">
              <h4>{{ experiment.name }}</h4>
              <a-tag>{{ experiment.targetType }}</a-tag>
            </div>
            <p>{{ formatTargetLabel(experiment) }} · 评测集 #{{ experiment.evalSetId }}</p>
            <p>{{ experiment.evaluatorIds.length }} 个评估器</p>
          </div>
          <div class="card-actions">
            <a-button type="link" size="small" :loading="runningId === experiment.id" @click="runExisting(experiment)">
              运行
            </a-button>
          </div>
        </article>
      </div>

      <section v-if="recentRun" class="run-summary-panel">
        <div>
          <h3>最新运行结果</h3>
          <p>{{ recentExperimentName }}</p>
        </div>
        <div class="summary-metrics">
          <a-tag :color="runStatusColor(recentRun.status)">{{ recentRun.status }}</a-tag>
          <strong>{{ formatRunSummary(recentRun).scoreText }}</strong>
          <span>通过率 {{ formatRunSummary(recentRun).passRateText }}</span>
          <span>{{ formatRunSummary(recentRun).failedText }}</span>
        </div>
      </section>
    </template>

    <section v-else class="experiment-stepper" data-testid="experiment-stepper">
      <header class="stepper-header">
        <div>
          <h3>创建实验</h3>
          <p>{{ currentStepMeta?.description }}</p>
        </div>
        <span data-testid="experiment-step-position">{{ currentStepDescription.positionText }}</span>
      </header>

      <a-steps :active="currentStepDescription.index" finish-status="success" class="stepper-steps">
        <a-step v-for="step in EXPERIMENT_CREATE_STEPS" :key="step.key" :title="step.title" />
      </a-steps>

      <div class="experiment-form stepper-body">
        <section v-if="currentStep === 'basic'" class="step-block">
          <strong>基础信息</strong>
          <label>
            <span>实验名称</span>
            <input v-model="form.name" data-testid="experiment-name" placeholder="请输入实验名称" />
          </label>
          <div class="run-settings-grid">
            <label>
              <span>最大并发</span>
              <input
                v-model.number="form.itemConcurrency"
                data-testid="experiment-item-concurrency"
                type="number"
                min="1"
                max="20"
              />
            </label>
            <label>
              <span>失败重试</span>
              <input
                v-model.number="form.itemRetryCount"
                data-testid="experiment-item-retry-count"
                type="number"
                min="0"
                max="5"
              />
            </label>
          </div>
        </section>

        <section v-else-if="currentStep === 'eval-set'" class="step-block">
          <strong>评测集</strong>
          <select v-model.number="form.evalSetId" data-testid="experiment-eval-set" @change="loadSelectedEvalSetFields">
            <option :value="0">选择评测集</option>
            <option v-for="evalSet in evalSets" :key="evalSet.id" :value="evalSet.id">
              {{ evalSet.name }}（{{ evalSet.caseCount }} 条用例）
            </option>
          </select>
        </section>

        <section v-else-if="currentStep === 'target'" class="step-block">
          <strong>评测对象</strong>
          <div class="target-picker">
            <select v-model="form.targetType" data-testid="experiment-target-type" @change="syncDefaultTarget">
              <option v-for="option in targetTypeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
            <select v-model.number="form.targetId" data-testid="experiment-target">
              <option :value="0">选择 {{ currentTargetLabel }}</option>
              <option v-for="target in targetOptions" :key="target.id" :value="target.id">
                {{ target.name }}
              </option>
            </select>
          </div>
          <label>
            <span>目标 userMessage 来源字段</span>
            <select v-model="form.targetFieldMapping.userMessage" data-testid="target-user-message-field">
              <option v-for="field in fieldOptions" :key="field.key" :value="field.key">
                {{ displayEvalSetFieldLabel(field) }} / {{ field.key }}
              </option>
            </select>
          </label>
        </section>

        <section v-else-if="currentStep === 'evaluator'" class="step-block">
          <strong>评估器</strong>
          <div class="checkbox-list">
            <div v-for="evaluator in evaluators" :key="evaluator.id" class="evaluator-selection-row">
              <label>
                <input
                  :checked="isEvaluatorSelected(evaluator.id)"
                  type="checkbox"
                  :value="evaluator.id"
                  :data-testid="`evaluator-checkbox-${evaluator.id}`"
                  @change="onEvaluatorToggle(evaluator.id, $event)"
                />
                <span>{{ evaluator.name }}</span>
              </label>
              <label v-if="isEvaluatorSelected(evaluator.id)" class="evaluator-version-picker">
                <span>版本</span>
                <select v-model.number="selectedEvaluatorVersions[evaluator.id]" :data-testid="`evaluator-version-${evaluator.id}`">
                  <option :value="0">当前草稿</option>
                  <option v-for="version in evaluatorVersions[evaluator.id] || []" :key="version.id" :value="version.id">
                    v{{ version.version }}
                  </option>
                </select>
              </label>
            </div>
          </div>
          <label>
            <span>评估器 expectedOutput 来源字段</span>
            <select v-model="form.evaluatorFieldMapping.expectedOutput" data-testid="evaluator-expected-output-field">
              <option v-for="field in fieldOptions" :key="field.key" :value="field.key">
                {{ displayEvalSetFieldLabel(field) }} / {{ field.key }}
              </option>
            </select>
          </label>
        </section>

        <section v-else class="step-block review">
          <strong>确认</strong>
          <dl class="confirm-grid">
            <div>
              <dt>实验名称</dt>
              <dd>{{ form.name || '未填写' }}</dd>
            </div>
            <div>
              <dt>评测集</dt>
              <dd>#{{ form.evalSetId || '-' }}</dd>
            </div>
            <div>
              <dt>目标</dt>
              <dd>{{ form.targetType }} #{{ form.targetId || '-' }}</dd>
            </div>
            <div>
              <dt>评估器</dt>
              <dd>{{ form.evaluatorIds.length }} 个已选</dd>
            </div>
            <div>
              <dt>评估器版本</dt>
              <dd>{{ selectedEvaluatorVersionSummary }}</dd>
            </div>
            <div>
              <dt>目标输入</dt>
              <dd>目标输入：{{ form.targetFieldMapping.userMessage }}</dd>
            </div>
            <div>
              <dt>评估期望</dt>
              <dd>期望字段：{{ form.evaluatorFieldMapping.expectedOutput }}</dd>
            </div>
            <div>
              <dt>并发</dt>
              <dd>并发：{{ form.itemConcurrency }}</dd>
            </div>
            <div>
              <dt>重试</dt>
              <dd>重试：{{ form.itemRetryCount }}</dd>
            </div>
          </dl>
          <p>创建后立即同步运行，支持 Agent、Workflow 和 Chatflow 目标。</p>
        </section>
      </div>

      <footer class="stepper-controls">
        <a-button data-testid="experiment-step-cancel" @click="cancelCreate">返回</a-button>
        <a-button
          data-testid="experiment-step-prev"
          :disabled="currentStepDescription.isFirst"
          @click="prevStep"
        >
          上一步
        </a-button>
        <a-button
          v-if="!currentStepDescription.isLast"
          type="primary"
          data-testid="experiment-step-next"
          @click="nextStep"
        >
          下一步
        </a-button>
        <a-button
          v-else
          type="primary"
          :loading="saving"
          data-testid="save-run-experiment"
          @click="createAndRun"
        >
          创建并运行
        </a-button>
      </footer>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'

import { getAgentList, type AgentListItem } from '@/api/agent'
import { listChatflows, listWorkflows, type WorkflowListItem } from '@/api/workflow'
import {
  createEvaluationExperiment,
  listEvalSetFields,
  listEvalSets,
  listEvaluatorVersions,
  listEvaluators,
  listEvaluationExperiments,
  runEvaluationExperiment,
  type EvalSet,
  type EvalSetField,
  type EvaluationExperiment,
  type EvaluationRun,
  type EvaluationTargetType,
  type Evaluator,
  type EvaluatorVersion,
} from '@/api/evaluation'
import {
  formatRunSummary,
  formatTargetLabel,
  runStatusTone,
  targetTypeOptions,
} from './experimentRunViewModel'
import {
  EXPERIMENT_CREATE_STEPS,
  advanceExperimentStep,
  describeExperimentStep,
  retreatExperimentStep,
  type ExperimentCreateStepKey,
} from './experimentStepperViewModel'
import {
  describeSelectedEvaluatorVersions,
  latestEvaluatorVersionSelection,
  selectedEvaluatorVersionIds,
} from './evaluatorVersionSelection'
import { displayEvalSetFieldLabel } from './evalSetViewModel'

const experiments = ref<EvaluationExperiment[]>([])
const agents = ref<AgentListItem[]>([])
const workflows = ref<WorkflowListItem[]>([])
const chatflows = ref<WorkflowListItem[]>([])
const evalSets = ref<EvalSet[]>([])
const selectedEvalSetFields = ref<EvalSetField[]>([])
const evaluators = ref<Evaluator[]>([])
const evaluatorVersions = ref<Record<number, EvaluatorVersion[]>>({})
const recentRun = ref<EvaluationRun | null>(null)
const recentExperimentName = ref('')
const loading = ref(false)
const saving = ref(false)
const runningId = ref<number | null>(null)
const searchName = ref('')
const stepperVisible = ref(false)
const currentStep = ref<ExperimentCreateStepKey>('basic')
const pageSize = 20

const form = reactive({
  name: '',
  targetType: 'AGENT' as EvaluationTargetType,
  targetId: 0,
  evalSetId: 0,
  evaluatorIds: [] as number[],
  targetFieldMapping: { userMessage: 'input' },
  evaluatorFieldMapping: { expectedOutput: 'expectedOutput', actualOutput: '__target.output' },
  itemConcurrency: 1,
  itemRetryCount: 0,
})
const selectedEvaluatorVersions = reactive<Record<number, number>>({})

const selectedExperiment = computed(() => experiments.value.find((item) => item.id === runningId.value))
const currentTargetLabel = computed(() => targetTypeOptions.find((item) => item.value === form.targetType)?.label || 'Target')
const currentStepDescription = computed(() => describeExperimentStep(currentStep.value))
const currentStepMeta = computed(() => EXPERIMENT_CREATE_STEPS.find((item) => item.key === currentStep.value))
const fieldOptions = computed(() => selectedEvalSetFields.value.length > 0
  ? selectedEvalSetFields.value
  : [
      { key: 'input', label: '输入', contentType: 'TEXT', required: true, displayOrder: 1 },
      { key: 'expectedOutput', label: '期望输出', contentType: 'TEXT', required: true, displayOrder: 2 },
    ])
const targetOptions = computed(() => {
  if (form.targetType === 'WORKFLOW') return workflows.value
  if (form.targetType === 'CHATFLOW') return chatflows.value
  return agents.value
})
const selectedEvaluatorVersionSummary = computed(() => describeSelectedEvaluatorVersions(
  form.evaluatorIds,
  selectedEvaluatorVersions,
  evaluatorVersions.value,
))

onMounted(() => {
  loadPrerequisites()
  loadExperiments()
})

function runStatusColor(status: string) {
  const tone = runStatusTone(status)
  return tone === 'danger' ? 'error' : tone
}

async function loadPrerequisites() {
  const [agentPage, workflowPage, chatflowPage, evalSetPage, evaluatorPage] = await Promise.all([
    getAgentList({ page: 1, pageSize, enabled: true }),
    listWorkflows({ page: 1, pageSize }),
    listChatflows({ page: 1, pageSize }),
    listEvalSets({ page: 1, pageSize }),
    listEvaluators({ page: 1, pageSize }),
  ])
  agents.value = agentPage.list
  workflows.value = workflowPage.list
  chatflows.value = chatflowPage.list
  evalSets.value = evalSetPage.list
  evaluators.value = evaluatorPage.list.filter((item) => item.enabled)
  await loadEvaluatorVersions()
}

async function loadEvaluatorVersions() {
  const pairs = await Promise.all(evaluators.value.map(async (evaluator) => [
    evaluator.id,
    (await listEvaluatorVersions(evaluator.id)).list,
  ] as const))
  evaluatorVersions.value = Object.fromEntries(pairs)
  syncEvaluatorVersionSelection()
}

async function loadExperiments() {
  loading.value = true
  try {
    const result = await listEvaluationExperiments({ page: 1, pageSize, name: searchName.value || undefined })
    experiments.value = result.list
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout>
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadExperiments, 300)
}

async function openCreate() {
  await loadEvaluatorVersions()
  form.name = ''
  form.targetType = 'AGENT'
  syncDefaultTarget()
  form.evalSetId = evalSets.value[0]?.id || 0
  form.evaluatorIds = evaluators.value[0] ? [evaluators.value[0].id] : []
  resetEvaluatorVersionSelection()
  form.targetFieldMapping = { userMessage: 'input' }
  form.evaluatorFieldMapping = { expectedOutput: 'expectedOutput', actualOutput: '__target.output' }
  form.itemConcurrency = 1
  form.itemRetryCount = 0
  await loadSelectedEvalSetFields()
  recentRun.value = null
  recentExperimentName.value = ''
  currentStep.value = 'basic'
  stepperVisible.value = true
}

function syncDefaultTarget() {
  form.targetId = targetOptions.value[0]?.id || 0
}

async function loadSelectedEvalSetFields() {
  if (!form.evalSetId) {
    selectedEvalSetFields.value = []
    return
  }
  const result = await listEvalSetFields(form.evalSetId)
  selectedEvalSetFields.value = result.list
  const keys = new Set(result.list.map((field) => field.key))
  if (!keys.has(form.targetFieldMapping.userMessage)) form.targetFieldMapping.userMessage = 'input'
  if (!keys.has(form.evaluatorFieldMapping.expectedOutput)) form.evaluatorFieldMapping.expectedOutput = 'expectedOutput'
}

function nextStep() {
  currentStep.value = advanceExperimentStep(currentStep.value)
}

function prevStep() {
  currentStep.value = retreatExperimentStep(currentStep.value)
}

function cancelCreate() {
  stepperVisible.value = false
}

function isEvaluatorSelected(evaluatorId: number) {
  return form.evaluatorIds.includes(evaluatorId)
}

function onEvaluatorToggle(evaluatorId: number, event: Event) {
  const checked = Boolean((event.target as HTMLInputElement).checked)
  if (checked && !form.evaluatorIds.includes(evaluatorId)) {
    form.evaluatorIds.push(evaluatorId)
  }
  if (!checked) {
    form.evaluatorIds = form.evaluatorIds.filter((item) => item !== evaluatorId)
  }
  syncEvaluatorVersionSelection()
}

function resetEvaluatorVersionSelection() {
  Object.keys(selectedEvaluatorVersions).forEach((key) => {
    delete selectedEvaluatorVersions[Number(key)]
  })
  Object.assign(selectedEvaluatorVersions, latestEvaluatorVersionSelection(form.evaluatorIds, evaluatorVersions.value))
}

function syncEvaluatorVersionSelection() {
  const selected = new Set(form.evaluatorIds)
  Object.keys(selectedEvaluatorVersions).forEach((key) => {
    const evaluatorId = Number(key)
    if (!selected.has(evaluatorId)) delete selectedEvaluatorVersions[evaluatorId]
  })
  const latest = latestEvaluatorVersionSelection(form.evaluatorIds, evaluatorVersions.value)
  form.evaluatorIds.forEach((evaluatorId) => {
    const current = Number(selectedEvaluatorVersions[evaluatorId] || 0)
    const validVersionIds = new Set((evaluatorVersions.value[evaluatorId] || []).map((item) => item.id))
    if (current === 0 && selectedEvaluatorVersions[evaluatorId] !== undefined) return
    if (!current || !validVersionIds.has(current)) {
      selectedEvaluatorVersions[evaluatorId] = latest[evaluatorId] || 0
    }
  })
}

async function createAndRun() {
  if (!form.name.trim() || !form.targetId || !form.evalSetId || form.evaluatorIds.length === 0) {
    message.error('请选择目标、评测集和评估器')
    return
  }
  saving.value = true
  try {
    const experiment = await createEvaluationExperiment({
      name: form.name.trim(),
      targetType: form.targetType,
      targetId: form.targetId,
      evalSetId: form.evalSetId,
      evaluatorIds: form.evaluatorIds,
      evaluatorVersionIds: selectedEvaluatorVersionIds(form.evaluatorIds, selectedEvaluatorVersions),
      targetFieldMapping: form.targetFieldMapping,
      evaluatorFieldMapping: form.evaluatorFieldMapping,
      itemConcurrency: Number(form.itemConcurrency) || 1,
      itemRetryCount: Number(form.itemRetryCount) || 0,
    })
    const run = await runEvaluationExperiment(experiment.id)
    recentRun.value = run
    recentExperimentName.value = experiment.name
    stepperVisible.value = false
    await loadExperiments()
    message.success('实验运行完成')
  } finally {
    saving.value = false
  }
}

async function runExisting(experiment: EvaluationExperiment) {
  runningId.value = experiment.id
  try {
    const run = await runEvaluationExperiment(experiment.id)
    recentRun.value = run
    recentExperimentName.value = selectedExperiment.value?.name || experiment.name
    await loadExperiments()
    message.success('实验运行完成')
  } finally {
    runningId.value = null
  }
}
</script>

<style scoped>
.experiments-panel {
  padding-top: 0.125rem;
}

.panel-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 0.625rem;
  margin-bottom: 0.875rem;
}

.search-input {
  width: 13.75rem;
}

.experiment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(17.5rem, 1fr));
  gap: var(--space-3);
}

.experiment-card {
  min-height: 8.25rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-md);
  padding: 0.875rem;
  background: #fff;
}

.card-title-row,
.card-actions,
.run-summary-panel,
.summary-metrics {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.card-title-row,
.run-summary-panel {
  justify-content: space-between;
}

.experiment-card h4,
.run-summary-panel h3 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
}

.experiment-card p,
.run-summary-panel p,
.review p {
  margin: var(--space-2) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.compact {
  min-height: 15rem;
}

.run-summary-panel {
  margin-top: 1.125rem;
  padding-top: var(--space-4);
  border-top: 0.0625rem solid var(--color-border-default);
}

.summary-metrics strong {
  color: var(--color-primary);
  font-size: var(--text-lg);
}

.experiment-stepper {
  display: grid;
  gap: var(--space-4);
  min-height: 30rem;
  border-bottom: 0.0625rem solid var(--color-border-default);
}

.stepper-header,
.stepper-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.stepper-header h3 {
  margin: 0 0 0.375rem;
  color: var(--color-text-primary);
  font-size: var(--text-lg);
}

.stepper-header p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.stepper-header span {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.stepper-steps {
  max-width: 58rem;
}

.stepper-body {
  max-width: 46rem;
}

.experiment-form {
  display: grid;
  gap: 0.875rem;
}

.experiment-form label,
.step-block {
  display: grid;
  gap: 0.4375rem;
}

.experiment-form input,
.experiment-form select {
  height: 2.125rem;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-sm);
  padding: 0 0.625rem;
  color: var(--color-text-primary);
  background: #fff;
}

.target-picker {
  display: grid;
  grid-template-columns: 10rem minmax(0, 1fr);
  gap: var(--space-2);
}

.run-settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 12rem));
  gap: var(--space-3);
}

.step-block {
  padding: var(--space-3);
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-md);
}

.step-block.review {
  border-color: rgba(99, 102, 241, 0.24);
  background: rgba(99, 102, 241, 0.08);
}

.confirm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: 0.75rem;
  margin: 0;
}

.confirm-grid div {
  display: grid;
  gap: 0.25rem;
}

.confirm-grid dt {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.confirm-grid dd {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.checkbox-list {
  display: grid;
  gap: var(--space-2);
}

.checkbox-list label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.checkbox-list input {
  width: 0.875rem;
  height: 0.875rem;
  padding: 0;
}
</style>
