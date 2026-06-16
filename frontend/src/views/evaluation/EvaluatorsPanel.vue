<template>
  <section class="evaluators-panel">
    <div class="panel-toolbar">
      <a-input
        v-model:value="searchName"
        placeholder="搜索评估器" allow-clear
        class="search-input"
        @input="onSearch"
      />
      <a-button data-testid="open-llm-evaluator-workbench" @click="openLlmWorkbench">
        LLM 工作台
      </a-button>
      <a-button type="primary" data-testid="create-evaluator" @click="openCreate">
        创建评估器
      </a-button>
    </div>

    <section v-if="workbenchVisible" class="llm-workbench" data-testid="llm-evaluator-workbench">
      <header class="workbench-header">
        <div>
          <h3>LLM 评估器工作台</h3>
          <p>调试模型、评分 Prompt 和样例输入，确认结果后发布不可变评估器版本。</p>
        </div>
        <a-button data-testid="close-llm-evaluator-workbench" @click="workbenchVisible = false">返回列表</a-button>
      </header>

      <div class="workbench-grid">
        <section class="workbench-form">
          <label>
            <span>名称</span>
            <input v-model="llmForm.name" data-testid="llm-workbench-name" placeholder="请输入 LLM 评估器名称" />
          </label>
          <label>
            <span>模型</span>
            <select v-model.number="llmForm.modelConfigId" data-testid="llm-workbench-model" class="native-select">
              <option :value="0">选择模型</option>
              <option v-for="model in modelOptions" :key="model.modelConfigId" :value="model.modelConfigId">
                {{ model.providerName }} / {{ model.modelName }}
              </option>
            </select>
          </label>
          <label>
            <span>Prompt</span>
            <textarea v-model="llmForm.prompt" data-testid="llm-workbench-prompt" rows="6" />
          </label>
          <div class="sample-grid">
            <label>
              <span>期望输出</span>
              <textarea v-model="llmForm.expectedOutput" data-testid="llm-workbench-expected" rows="4" />
            </label>
            <label>
              <span>实际输出</span>
              <textarea v-model="llmForm.actualOutput" data-testid="llm-workbench-actual" rows="4" />
            </label>
          </div>
          <label class="score-input">
            <span>通过阈值</span>
            <input v-model.number="llmForm.passingScore" type="number" min="0" max="1" step="0.05" />
          </label>
          <div class="workbench-actions">
            <a-button type="primary" :loading="debugging" data-testid="llm-workbench-debug" @click="runLlmDebug">
              调试
            </a-button>
            <a-button :loading="saving" data-testid="llm-workbench-publish" @click="publishLlmWorkbench">
              创建并发布版本
            </a-button>
          </div>
          <p v-if="publishedVersionLabel" class="published-version" data-testid="llm-workbench-published-version">
            已发布 {{ publishedVersionLabel }}
          </p>
        </section>

        <section class="workbench-preview">
          <h4>调试结果</h4>
          <div v-if="llmDebugResult" class="llm-debug-result" data-testid="llm-debug-result">
            <strong>{{ llmDebugResult.passed ? '通过' : '失败' }}</strong>
            <span>分数 {{ llmDebugResult.score }}</span>
            <p>{{ llmDebugResult.reason }}</p>
          </div>
          <p v-else class="muted">运行 Debug 后查看 score、reason 和 raw output。</p>
          <details v-if="llmDebugResult" class="raw-output" data-testid="llm-debug-raw" open>
            <summary>原始输出</summary>
            <pre>{{ llmDebugResult.rawOutput }}</pre>
          </details>
        </section>
      </div>
    </section>

    <template v-else>
    <a-tabs v-model:activeKey="catalogTab" class="evaluator-catalog-tabs">
      <a-tab-pane key="custom">
        <template #tab>
          <span data-testid="evaluator-custom-tab">自定义</span>
        </template>
      </a-tab-pane>
      <a-tab-pane key="presets">
        <template #tab>
          <span data-testid="evaluator-preset-tab">预置</span>
        </template>
      </a-tab-pane>
    </a-tabs>

    <div v-if="catalogTab === 'custom' && evaluators.length === 0 && !loading" class="empty-panel compact">
      <h3>定义可解释评分规则</h3>
      <p>先支持精确匹配和关键词包含，保存前可以用样例测试评分反馈。</p>
      <a-button type="primary" @click="openCreate">创建评估器</a-button>
    </div>

    <div v-else-if="catalogTab === 'custom'" class="evaluator-grid">
      <article v-for="evaluator in evaluators" :key="evaluator.id" class="evaluator-card">
        <div>
          <div class="card-title-row">
            <h4>{{ evaluator.name }}</h4>
            <div class="card-tags">
              <a-tag v-if="latestVersion(evaluator.id)" color="success">
                v{{ latestVersion(evaluator.id)?.version }}
              </a-tag>
              <a-tag :color="evaluator.enabled ? 'success' : 'default'">
                {{ evaluator.enabled ? '启用' : '禁用' }}
              </a-tag>
            </div>
          </div>
          <p>{{ describeEvaluatorType(evaluator.type) }}</p>
          <p v-if="evaluator.type === 'CONTAINS_KEYWORDS'" class="keyword-line">
            {{ keywordTextFromConfig(evaluator.config) || '未配置关键词' }}
          </p>
        </div>
        <div class="card-actions">
          <a-button type="link"
            size="small"
            :data-testid="`publish-evaluator-version-${evaluator.id}`"
            @click="publishVersion(evaluator)"
          >
            发布版本
          </a-button>
          <a-button type="link" size="small" @click="openEdit(evaluator)">编辑</a-button>
          <a-button danger type="link" size="small" @click="removeEvaluator(evaluator)">删除</a-button>
        </div>
      </article>
    </div>

    <div v-else class="evaluator-grid" data-testid="evaluator-preset-catalog">
      <article v-for="preset in presets" :key="preset.key" class="evaluator-card">
        <div>
          <div class="card-title-row">
            <h4>{{ displayPresetName(preset) }}</h4>
            <a-tag :color="preset.enabled ? 'success' : 'default'">
              {{ preset.enabled ? '启用' : '禁用' }}
            </a-tag>
          </div>
          <p>{{ displayPresetDescription(preset) }}</p>
        </div>
      </article>
    </div>

    <a-modal
      v-model:open="dialogVisible"
      :title="editingEvaluator ? '编辑评估器' : '创建评估器'"
      width="35rem"
      :mask-closable="false"
      destroy-on-close
    >
      <a-form :label-col="{ style: { width: '5.75rem' } }">
        <a-form-item label="名称" required>
          <a-input v-model:value="form.name" placeholder="请输入评估器名称" />
        </a-form-item>
        <a-form-item label="类型">
          <a-segmented v-model:value="form.type" :options="typeOptions" />
        </a-form-item>
        <a-form-item v-if="form.type === 'CONTAINS_KEYWORDS'" title="关键词" required>
          <a-input v-model:value="form.keywords" placeholder="用英文逗号分隔，如 refund,policy" />
        </a-form-item>
        <a-form-item v-if="form.type === 'LLM_JUDGE'" title="模型" required>
          <select v-model.number="form.modelConfigId" data-testid="llm-judge-model" class="native-select">
            <option :value="0">选择模型</option>
            <option v-for="model in modelOptions" :key="model.modelConfigId" :value="model.modelConfigId">
              {{ model.providerName }} / {{ model.modelName }}
            </option>
          </select>
        </a-form-item>
        <a-form-item v-if="form.type === 'LLM_JUDGE'" title="Rubric">
          <a-textarea v-model:value="form.rubric" :rows="3" placeholder="描述通过标准" />
        </a-form-item>
        <a-form-item label="忽略大小写">
          <a-switch v-model:checked="form.ignoreCase" />
        </a-form-item>
        <a-form-item v-if="editingEvaluator" title="状态">
          <a-switch v-model:checked="form.enabled" :checked-value="1" :un-checked-value="0" />
        </a-form-item>
        <a-divider content-position="left">样例测试</a-divider>
        <a-form-item label="期望输出">
          <a-textarea v-model:value="form.expectedOutput" :rows="2" placeholder="精确匹配会使用该字段" />
        </a-form-item>
        <a-form-item label="实际输出" required>
          <a-textarea v-model:value="form.actualOutput" :rows="3" placeholder="粘贴一次 Agent 回复用于试跑" />
        </a-form-item>
        <a-form-item>
          <a-button data-testid="test-evaluator-sample" @click="runSampleTest">测试样例</a-button>
        </a-form-item>
        <div v-if="sampleResult" class="sample-result" :class="{ passed: sampleResult.passed }">
          <strong>{{ sampleResult.passed ? '通过' : '失败' }}</strong>
          <span>分数 {{ sampleResult.score }}</span>
          <p>{{ sampleResult.reason }}</p>
        </div>
      </a-form>
      <template #footer>
        <a-button @click="dialogVisible = false">取消</a-button>
        <a-button type="primary" :loading="saving" data-testid="save-evaluator" @click="submitEvaluator">
          确定
        </a-button>
      </template>
    </a-modal>
    </template>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { message, Modal } from 'ant-design-vue'

import {
  createEvaluator,
  debugLlmEvaluator,
  deleteEvaluator,
  listEvaluatorPresets,
  listEvaluatorVersions,
  listEvaluators,
  publishEvaluatorVersion,
  testEvaluatorDraft,
  updateEvaluator,
  type Evaluator,
  type LlmEvaluatorDebugResult,
  type EvaluatorPreset,
  type EvaluatorSampleResult,
  type EvaluatorType,
  type EvaluatorVersion,
} from '@/api/evaluation'
import { getModelOptions, type ModelOption } from '@/api/agent'
import { describeEvaluatorType, keywordConfigFromText, keywordTextFromConfig } from './evaluatorViewModel'
import {
  buildLlmEvaluatorConfig,
  describeLlmDebugResult,
  initialLlmWorkbenchForm,
  type LlmWorkbenchForm,
} from './llmEvaluatorWorkbench'

const typeOptions = [
  { label: '精确匹配', value: 'EXACT_MATCH' },
  { label: '包含关键词', value: 'CONTAINS_KEYWORDS' },
  { label: 'LLM 裁判', value: 'LLM_JUDGE' },
]

const evaluators = ref<Evaluator[]>([])
const evaluatorVersions = ref<Record<number, EvaluatorVersion[]>>({})
const presets = ref<EvaluatorPreset[]>([])
const modelOptions = ref<ModelOption[]>([])
const loading = ref(false)
const saving = ref(false)
const debugging = ref(false)
const searchName = ref('')
const dialogVisible = ref(false)
const workbenchVisible = ref(false)
const catalogTab = ref<'custom' | 'presets'>('custom')
const editingEvaluator = ref<Evaluator | null>(null)
const sampleResult = ref<EvaluatorSampleResult | null>(null)
const llmDebugResult = ref<LlmEvaluatorDebugResult | null>(null)
const publishedVersionLabel = ref('')
const pageSize = 20

const form = reactive({
  name: '',
  type: 'CONTAINS_KEYWORDS' as EvaluatorType,
  keywords: '',
  ignoreCase: true,
  enabled: 1,
  expectedOutput: '',
  actualOutput: '',
  modelConfigId: 0,
  rubric: '实际输出满足期望答案时通过。',
})
const llmForm = reactive<LlmWorkbenchForm>(initialLlmWorkbenchForm())

onMounted(() => {
  loadEvaluators()
  loadPresets()
  loadModels()
})

async function loadModels() {
  modelOptions.value = await getModelOptions({ includeMock: true })
  if (!llmForm.modelConfigId) llmForm.modelConfigId = modelOptions.value[0]?.modelConfigId || 0
}

async function openLlmWorkbench() {
  if (modelOptions.value.length === 0) await loadModels()
  const initial = initialLlmWorkbenchForm(modelOptions.value[0]?.modelConfigId || 0)
  Object.assign(llmForm, initial)
  llmDebugResult.value = null
  publishedVersionLabel.value = ''
  workbenchVisible.value = true
}

async function loadEvaluators() {
  loading.value = true
  try {
    const result = await listEvaluators({ page: 1, pageSize, name: searchName.value || undefined })
    evaluators.value = result.list
    await loadVersions(result.list)
  } finally {
    loading.value = false
  }
}

async function loadVersions(items: Evaluator[]) {
  const pairs = await Promise.all(items.map(async (item) => [item.id, (await listEvaluatorVersions(item.id)).list] as const))
  evaluatorVersions.value = Object.fromEntries(pairs)
}

async function loadPresets() {
  const result = await listEvaluatorPresets()
  presets.value = result.list
}

let searchTimer: ReturnType<typeof setTimeout>
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadEvaluators, 300)
}

function openCreate() {
  editingEvaluator.value = null
  sampleResult.value = null
  form.name = ''
  form.type = 'CONTAINS_KEYWORDS'
  form.keywords = ''
  form.ignoreCase = true
  form.enabled = 1
  form.expectedOutput = ''
  form.actualOutput = ''
  form.modelConfigId = modelOptions.value[0]?.modelConfigId || 0
  form.rubric = '实际输出满足期望答案时通过。'
  dialogVisible.value = true
}

function openEdit(evaluator: Evaluator) {
  editingEvaluator.value = evaluator
  sampleResult.value = null
  form.name = evaluator.name
  form.type = evaluator.type
  form.keywords = keywordTextFromConfig(evaluator.config)
  form.ignoreCase = Boolean(evaluator.config.ignoreCase)
  form.enabled = evaluator.enabled
  form.expectedOutput = ''
  form.actualOutput = ''
  form.modelConfigId = Number(evaluator.config.modelConfigId || modelOptions.value[0]?.modelConfigId || 0)
  form.rubric = String(evaluator.config.rubric || '实际输出满足期望答案时通过。')
  dialogVisible.value = true
}

async function runSampleTest() {
  if (!form.actualOutput.trim()) {
    message.error('请输入实际输出')
    return
  }
  sampleResult.value = await testEvaluatorDraft({
    type: form.type,
    config: buildConfig(),
    expectedOutput: form.expectedOutput,
    actualOutput: form.actualOutput,
  })
}

async function submitEvaluator() {
  if (!form.name.trim()) {
    message.error('请输入评估器名称')
    return
  }
  saving.value = true
  try {
    const payload = { name: form.name.trim(), type: form.type, config: buildConfig() }
    if (editingEvaluator.value) {
      await updateEvaluator(editingEvaluator.value.id, { ...payload, enabled: form.enabled })
      message.success('保存成功')
    } else {
      await createEvaluator(payload)
      message.success('创建成功')
    }
    dialogVisible.value = false
    await loadEvaluators()
  } finally {
    saving.value = false
  }
}

function removeEvaluator(evaluator: Evaluator) {
  Modal.confirm({
    title: '提示',
    content: `确定删除评估器「${evaluator.name}」？`,
    okText: '确定',
    cancelText: '取消',
    okType: 'danger',
    onOk: async () => {
      await deleteEvaluator(evaluator.id)
      message.success('删除成功')
      await loadEvaluators()
    },
  })
}

async function publishVersion(evaluator: Evaluator) {
  const version = await publishEvaluatorVersion(evaluator.id, { description: '从评测工作台发布' })
  evaluatorVersions.value = {
    ...evaluatorVersions.value,
    [evaluator.id]: [version, ...(evaluatorVersions.value[evaluator.id] || [])],
  }
  message.success(`已发布 v${version.version}`)
}

async function runLlmDebug() {
  if (!llmForm.modelConfigId || !llmForm.actualOutput.trim() || !llmForm.prompt.trim()) {
    message.error('请选择模型并填写 Prompt 与实际输出')
    return
  }
  debugging.value = true
  try {
    llmDebugResult.value = await debugLlmEvaluator({
      modelConfigId: llmForm.modelConfigId,
      prompt: llmForm.prompt,
      expectedOutput: llmForm.expectedOutput,
      actualOutput: llmForm.actualOutput,
      passingScore: llmForm.passingScore,
    })
    message.success(describeLlmDebugResult(llmDebugResult.value))
  } finally {
    debugging.value = false
  }
}

async function publishLlmWorkbench() {
  if (!llmForm.name.trim() || !llmForm.modelConfigId || !llmForm.prompt.trim()) {
    message.error('请填写名称、模型和 Prompt')
    return
  }
  saving.value = true
  try {
    const evaluator = await createEvaluator({
      name: llmForm.name.trim(),
      type: 'LLM_JUDGE',
      config: buildLlmEvaluatorConfig(llmForm),
    })
    const version = await publishEvaluatorVersion(evaluator.id, { description: '从 LLM 评估器工作台发布' })
    publishedVersionLabel.value = `v${version.version}`
    evaluators.value = [evaluator, ...evaluators.value]
    evaluatorVersions.value = {
      ...evaluatorVersions.value,
      [evaluator.id]: [version],
    }
    message.success(`已发布 ${publishedVersionLabel.value}`)
  } finally {
    saving.value = false
  }
}

function latestVersion(evaluatorId: number): EvaluatorVersion | null {
  return evaluatorVersions.value[evaluatorId]?.[0] || null
}

function displayPresetName(preset: EvaluatorPreset): string {
  if (preset.key === 'EXACT_MATCH') return '精确匹配'
  if (preset.key === 'CONTAINS_KEYWORDS') return '包含关键词'
  if (preset.key === 'LLM_JUDGE') return 'LLM 裁判'
  if (preset.key === 'CODE_EVALUATOR') return '代码评估器'
  return preset.name
}

function displayPresetDescription(preset: EvaluatorPreset): string {
  if (preset.key === 'EXACT_MATCH') return '实际输出与期望输出完全一致时通过。'
  if (preset.key === 'CONTAINS_KEYWORDS') return '实际输出包含配置关键词时通过。'
  if (preset.key === 'LLM_JUDGE') return '使用模型根据 Rubric 输出分数和原因。'
  if (preset.key === 'CODE_EVALUATOR') return '沙箱和超时控制明确后开放。'
  return preset.description
}

function buildConfig(): Record<string, unknown> {
  if (form.type === 'EXACT_MATCH') {
    return { ignoreCase: form.ignoreCase }
  }
  if (form.type === 'LLM_JUDGE') {
    return {
      modelConfigId: form.modelConfigId,
      rubric: form.rubric,
      passingScore: 0.7,
    }
  }
  const config = keywordConfigFromText(form.keywords)
  return { ...config, ignoreCase: form.ignoreCase }
}
</script>

<style scoped>
.evaluators-panel {
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

.evaluator-catalog-tabs {
  margin-bottom: 0.875rem;
}

.llm-workbench {
  display: grid;
  gap: var(--space-4);
}

.workbench-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 0.0625rem solid var(--color-border-default);
}

.workbench-header h3,
.workbench-preview h4 {
  margin: 0;
  color: var(--color-text-primary);
}

.workbench-header p,
.muted {
  margin: var(--space-2) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(24rem, 1fr) minmax(20rem, 0.8fr);
  gap: var(--space-4);
  align-items: start;
}

.workbench-form,
.workbench-preview {
  display: grid;
  gap: var(--space-3);
}

.workbench-form label {
  display: grid;
  gap: 0.4375rem;
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.workbench-form input,
.workbench-form select,
.workbench-form textarea {
  width: 100%;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-sm);
  padding: 0.5rem 0.625rem;
  color: var(--color-text-primary);
  background: #fff;
  resize: vertical;
}

.workbench-form input,
.workbench-form select {
  height: 2.125rem;
  padding-top: 0;
  padding-bottom: 0;
}

.sample-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.score-input {
  max-width: 12rem;
}

.workbench-actions {
  display: flex;
  gap: var(--space-2);
}

.llm-debug-result {
  display: grid;
  gap: var(--space-2);
  border: 0.0625rem solid rgba(99, 102, 241, 0.24);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: rgba(99, 102, 241, 0.08);
}

.llm-debug-result strong {
  color: #16a34a;
}

.llm-debug-result p {
  margin: 0;
  color: var(--color-text-primary);
}

.raw-output {
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: #fff;
}

.raw-output pre {
  margin: var(--space-2) 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--color-text-primary);
}

.published-version {
  margin: 0;
  color: #16a34a;
  font-weight: 600;
}

.evaluator-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(17.5rem, 1fr));
  gap: var(--space-3);
}

.evaluator-card {
  min-height: 8.5rem;
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
.card-tags {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.625rem;
}

.card-tags {
  justify-content: flex-end;
  flex-wrap: wrap;
}

.card-title-row h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
}

.evaluator-card p {
  margin: var(--space-2) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.keyword-line {
  color: var(--color-primary);
}

.native-select {
  width: 100%;
  height: 2rem;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-sm);
  padding: 0 0.625rem;
  color: var(--color-text-primary);
  background: #fff;
}

.compact {
  min-height: 13.75rem;
}

.sample-result {
  margin-left: 5.75rem;
  padding: 0.625rem 0.75rem;
  border: 0.0625rem solid rgba(220, 38, 38, 0.24);
  border-radius: var(--radius-md);
  background: rgba(220, 38, 38, 0.08);
  color: #dc2626;
}

.sample-result.passed {
  border-color: rgba(22, 163, 74, 0.24);
  background: rgba(22, 163, 74, 0.08);
  color: #16a34a;
}

.sample-result span {
  margin-left: 0.625rem;
}

.sample-result p {
  margin: 0.375rem 0 0;
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}
</style>
