<template>
  <section class="experiments-panel">
    <div class="panel-toolbar">
      <el-input
        v-model="searchName"
        placeholder="搜索实验"
        clearable
        class="search-input"
        @input="onSearch"
      />
      <el-button type="primary" data-testid="create-experiment" @click="openCreate">
        创建实验
      </el-button>
    </div>

    <div v-if="experiments.length === 0 && !loading" class="empty-panel compact">
      <h3>先跑一次目标实验</h3>
      <p>选择 Agent、Workflow 或 Chatflow、评测集和评估器后运行，报告会展示分数、通过率和失败用例。</p>
      <el-button type="primary" @click="openCreate">创建实验</el-button>
    </div>

    <div v-else class="experiment-grid">
      <article v-for="experiment in experiments" :key="experiment.id" class="experiment-card">
        <div>
          <div class="card-title-row">
            <h4>{{ experiment.name }}</h4>
            <el-tag effect="plain">{{ experiment.targetType }}</el-tag>
          </div>
          <p>{{ formatTargetLabel(experiment) }} · Eval Set #{{ experiment.evalSetId }}</p>
          <p>{{ experiment.evaluatorIds.length }} evaluator(s)</p>
        </div>
        <div class="card-actions">
          <el-button type="primary" link size="small" :loading="runningId === experiment.id" @click="runExisting(experiment)">
            运行
          </el-button>
        </div>
      </article>
    </div>

    <section v-if="recentRun" class="run-summary-panel">
      <div>
        <h3>最新运行结果</h3>
        <p>{{ recentExperimentName }}</p>
      </div>
      <div class="summary-metrics">
        <el-tag :type="runStatusTone(recentRun.status)">{{ recentRun.status }}</el-tag>
        <strong>{{ formatRunSummary(recentRun).scoreText }}</strong>
        <span>Pass {{ formatRunSummary(recentRun).passRateText }}</span>
        <span>{{ formatRunSummary(recentRun).failedText }}</span>
      </div>
    </section>

    <el-dialog
      v-model="dialogVisible"
      title="创建实验"
      width="640px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="experiment-form">
        <label>
          <span>实验名称</span>
          <input v-model="form.name" data-testid="experiment-name" placeholder="请输入实验名称" />
        </label>

        <div class="step-block">
          <strong>1. Target</strong>
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
        </div>

        <div class="step-block">
          <strong>2. Eval Set</strong>
          <select v-model.number="form.evalSetId" data-testid="experiment-eval-set">
            <option :value="0">选择评测集</option>
            <option v-for="evalSet in evalSets" :key="evalSet.id" :value="evalSet.id">
              {{ evalSet.name }} ({{ evalSet.caseCount }} cases)
            </option>
          </select>
        </div>

        <div class="step-block">
          <strong>3. Evaluators</strong>
          <div class="checkbox-list">
            <label v-for="evaluator in evaluators" :key="evaluator.id">
              <input v-model="form.evaluatorIds" type="checkbox" :value="evaluator.id" />
              <span>{{ evaluator.name }}</span>
            </label>
          </div>
        </div>

        <div class="step-block review">
          <strong>4. Review / Run</strong>
          <p>创建后立即同步运行，支持 Agent、Workflow 和 Chatflow 目标。</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="saving"
          data-testid="save-run-experiment"
          @click="createAndRun"
        >
          创建并运行
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { getAgentList, type AgentListItem } from '@/api/agent'
import { listChatflows, listWorkflows, type WorkflowListItem } from '@/api/workflow'
import {
  createEvaluationExperiment,
  listEvalSets,
  listEvaluators,
  listEvaluationExperiments,
  runEvaluationExperiment,
  type EvalSet,
  type EvaluationExperiment,
  type EvaluationRun,
  type EvaluationTargetType,
  type Evaluator,
} from '@/api/evaluation'
import {
  formatRunSummary,
  formatTargetLabel,
  runStatusTone,
  targetTypeOptions,
} from './experimentRunViewModel'

const experiments = ref<EvaluationExperiment[]>([])
const agents = ref<AgentListItem[]>([])
const workflows = ref<WorkflowListItem[]>([])
const chatflows = ref<WorkflowListItem[]>([])
const evalSets = ref<EvalSet[]>([])
const evaluators = ref<Evaluator[]>([])
const recentRun = ref<EvaluationRun | null>(null)
const recentExperimentName = ref('')
const loading = ref(false)
const saving = ref(false)
const runningId = ref<number | null>(null)
const searchName = ref('')
const dialogVisible = ref(false)
const pageSize = 20

const form = reactive({
  name: '',
  targetType: 'AGENT' as EvaluationTargetType,
  targetId: 0,
  evalSetId: 0,
  evaluatorIds: [] as number[],
})

const selectedExperiment = computed(() => experiments.value.find((item) => item.id === runningId.value))
const currentTargetLabel = computed(() => targetTypeOptions.find((item) => item.value === form.targetType)?.label || 'Target')
const targetOptions = computed(() => {
  if (form.targetType === 'WORKFLOW') return workflows.value
  if (form.targetType === 'CHATFLOW') return chatflows.value
  return agents.value
})

onMounted(() => {
  loadPrerequisites()
  loadExperiments()
})

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

function openCreate() {
  form.name = ''
  form.targetType = 'AGENT'
  syncDefaultTarget()
  form.evalSetId = evalSets.value[0]?.id || 0
  form.evaluatorIds = evaluators.value[0] ? [evaluators.value[0].id] : []
  recentRun.value = null
  recentExperimentName.value = ''
  dialogVisible.value = true
}

function syncDefaultTarget() {
  form.targetId = targetOptions.value[0]?.id || 0
}

async function createAndRun() {
  if (!form.name.trim() || !form.targetId || !form.evalSetId || form.evaluatorIds.length === 0) {
    ElMessage.error('请选择目标、评测集和评估器')
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
    })
    const run = await runEvaluationExperiment(experiment.id)
    recentRun.value = run
    recentExperimentName.value = experiment.name
    dialogVisible.value = false
    await loadExperiments()
    ElMessage.success('实验运行完成')
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
    ElMessage.success('实验运行完成')
  } finally {
    runningId.value = null
  }
}
</script>

<style scoped>
.experiments-panel {
  padding-top: 2px;
}

.panel-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-bottom: 14px;
}

.search-input {
  width: 220px;
}

.experiment-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.experiment-card {
  min-height: 132px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 14px;
  background: #fff;
}

.card-title-row,
.card-actions,
.run-summary-panel,
.summary-metrics {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-title-row,
.run-summary-panel {
  justify-content: space-between;
}

.experiment-card h4,
.run-summary-panel h3 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 15px;
}

.experiment-card p,
.run-summary-panel p,
.review p {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.compact {
  min-height: 240px;
}

.run-summary-panel {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.summary-metrics strong {
  color: var(--el-color-primary);
  font-size: 18px;
}

.experiment-form {
  display: grid;
  gap: 14px;
}

.experiment-form label,
.step-block {
  display: grid;
  gap: 7px;
}

.experiment-form input,
.experiment-form select {
  height: 34px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  padding: 0 10px;
  color: var(--el-text-color-primary);
  background: #fff;
}

.target-picker {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr);
  gap: 8px;
}

.step-block {
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.checkbox-list {
  display: grid;
  gap: 8px;
}

.checkbox-list label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.checkbox-list input {
  width: 14px;
  height: 14px;
  padding: 0;
}
</style>
