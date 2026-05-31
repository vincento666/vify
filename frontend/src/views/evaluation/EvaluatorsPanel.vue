<template>
  <section class="evaluators-panel">
    <div class="panel-toolbar">
      <el-input
        v-model="searchName"
        placeholder="搜索评估器"
        clearable
        class="search-input"
        @input="onSearch"
      />
      <el-button type="primary" data-testid="create-evaluator" @click="openCreate">
        创建评估器
      </el-button>
    </div>

    <div v-if="evaluators.length === 0 && !loading" class="empty-panel compact">
      <h3>定义可解释评分规则</h3>
      <p>先支持精确匹配和关键词包含，保存前可以用样例测试评分反馈。</p>
      <el-button type="primary" @click="openCreate">创建评估器</el-button>
    </div>

    <div v-else class="evaluator-grid">
      <article v-for="evaluator in evaluators" :key="evaluator.id" class="evaluator-card">
        <div>
          <div class="card-title-row">
            <h4>{{ evaluator.name }}</h4>
            <el-tag :type="evaluator.enabled ? 'success' : 'info'" effect="plain">
              {{ evaluator.enabled ? '启用' : '禁用' }}
            </el-tag>
          </div>
          <p>{{ describeEvaluatorType(evaluator.type) }}</p>
          <p v-if="evaluator.type === 'CONTAINS_KEYWORDS'" class="keyword-line">
            {{ keywordTextFromConfig(evaluator.config) || '未配置关键词' }}
          </p>
        </div>
        <div class="card-actions">
          <el-button link size="small" @click="openEdit(evaluator)">编辑</el-button>
          <el-button type="danger" link size="small" @click="removeEvaluator(evaluator)">删除</el-button>
        </div>
      </article>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingEvaluator ? '编辑评估器' : '创建评估器'"
      width="560px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form label-width="92px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="请输入评估器名称" />
        </el-form-item>
        <el-form-item label="类型">
          <el-segmented v-model="form.type" :options="typeOptions" />
        </el-form-item>
        <el-form-item v-if="form.type === 'CONTAINS_KEYWORDS'" label="关键词" required>
          <el-input v-model="form.keywords" placeholder="用英文逗号分隔，如 refund,policy" />
        </el-form-item>
        <el-form-item v-if="form.type === 'LLM_JUDGE'" label="模型" required>
          <select v-model.number="form.modelConfigId" data-testid="llm-judge-model" class="native-select">
            <option :value="0">选择模型</option>
            <option v-for="model in modelOptions" :key="model.modelConfigId" :value="model.modelConfigId">
              {{ model.providerName }} / {{ model.modelName }}
            </option>
          </select>
        </el-form-item>
        <el-form-item v-if="form.type === 'LLM_JUDGE'" label="Rubric">
          <el-input v-model="form.rubric" type="textarea" :rows="3" placeholder="描述通过标准" />
        </el-form-item>
        <el-form-item label="忽略大小写">
          <el-switch v-model="form.ignoreCase" />
        </el-form-item>
        <el-form-item v-if="editingEvaluator" label="状态">
          <el-switch v-model="form.enabled" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-divider content-position="left">样例测试</el-divider>
        <el-form-item label="期望输出">
          <el-input v-model="form.expectedOutput" type="textarea" :rows="2" placeholder="Exact Match 会使用该字段" />
        </el-form-item>
        <el-form-item label="实际输出" required>
          <el-input v-model="form.actualOutput" type="textarea" :rows="3" placeholder="粘贴一次 Agent 回复用于试跑" />
        </el-form-item>
        <el-form-item>
          <el-button data-testid="test-evaluator-sample" @click="runSampleTest">测试样例</el-button>
        </el-form-item>
        <div v-if="sampleResult" class="sample-result" :class="{ passed: sampleResult.passed }">
          <strong>{{ sampleResult.passed ? 'PASS' : 'FAIL' }}</strong>
          <span>Score {{ sampleResult.score }}</span>
          <p>{{ sampleResult.reason }}</p>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-testid="save-evaluator" @click="submitEvaluator">
          确定
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  createEvaluator,
  deleteEvaluator,
  listEvaluators,
  testEvaluatorDraft,
  updateEvaluator,
  type Evaluator,
  type EvaluatorSampleResult,
  type EvaluatorType,
} from '@/api/evaluation'
import { getModelOptions, type ModelOption } from '@/api/agent'
import { describeEvaluatorType, keywordConfigFromText, keywordTextFromConfig } from './evaluatorViewModel'

const typeOptions = [
  { label: 'Exact Match', value: 'EXACT_MATCH' },
  { label: 'Contains Keywords', value: 'CONTAINS_KEYWORDS' },
  { label: 'LLM Judge', value: 'LLM_JUDGE' },
]

const evaluators = ref<Evaluator[]>([])
const modelOptions = ref<ModelOption[]>([])
const loading = ref(false)
const saving = ref(false)
const searchName = ref('')
const dialogVisible = ref(false)
const editingEvaluator = ref<Evaluator | null>(null)
const sampleResult = ref<EvaluatorSampleResult | null>(null)
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
  rubric: 'Pass when the actual output satisfies the expected answer.',
})

onMounted(() => {
  loadEvaluators()
  loadModels()
})

async function loadModels() {
  modelOptions.value = await getModelOptions()
}

async function loadEvaluators() {
  loading.value = true
  try {
    const result = await listEvaluators({ page: 1, pageSize, name: searchName.value || undefined })
    evaluators.value = result.list
  } finally {
    loading.value = false
  }
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
  form.rubric = 'Pass when the actual output satisfies the expected answer.'
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
  form.rubric = String(evaluator.config.rubric || 'Pass when the actual output satisfies the expected answer.')
  dialogVisible.value = true
}

async function runSampleTest() {
  if (!form.actualOutput.trim()) {
    ElMessage.error('请输入实际输出')
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
    ElMessage.error('请输入评估器名称')
    return
  }
  saving.value = true
  try {
    const payload = { name: form.name.trim(), type: form.type, config: buildConfig() }
    if (editingEvaluator.value) {
      await updateEvaluator(editingEvaluator.value.id, { ...payload, enabled: form.enabled })
      ElMessage.success('保存成功')
    } else {
      await createEvaluator(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadEvaluators()
  } finally {
    saving.value = false
  }
}

async function removeEvaluator(evaluator: Evaluator) {
  try {
    await ElMessageBox.confirm(`确定删除评估器「${evaluator.name}」？`, '提示', { type: 'warning' })
    await deleteEvaluator(evaluator.id)
    ElMessage.success('删除成功')
    await loadEvaluators()
  } catch { /* cancel */ }
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

.evaluator-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.evaluator-card {
  min-height: 136px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 14px;
  background: #fff;
}

.card-title-row,
.card-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.card-title-row h4 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 15px;
}

.evaluator-card p {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.keyword-line {
  color: var(--el-color-primary);
}

.native-select {
  width: 100%;
  height: 32px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  padding: 0 10px;
  color: var(--el-text-color-primary);
  background: #fff;
}

.compact {
  min-height: 220px;
}

.sample-result {
  margin-left: 92px;
  padding: 10px 12px;
  border: 1px solid var(--el-color-danger-light-5);
  border-radius: 8px;
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

.sample-result.passed {
  border-color: var(--el-color-success-light-5);
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.sample-result span {
  margin-left: 10px;
}

.sample-result p {
  margin: 6px 0 0;
  color: var(--el-text-color-primary);
  font-size: 13px;
}
</style>
