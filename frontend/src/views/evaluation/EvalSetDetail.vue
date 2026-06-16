<template>
  <section class="eval-set-detail-page">
    <header class="detail-header">
      <div class="detail-title-block">
        <nav class="detail-breadcrumb" data-testid="eval-set-detail-breadcrumb" aria-label="评测集路径">
          <button
            type="button"
            aria-label="返回评测集"
            @click="router.push({ name: 'HifyEvaluation', query: { tab: 'eval-sets' } })"
          >
            评测集
          </button>
          <span>/</span>
          <strong>{{ selectedSet?.name || '评测集详情' }}</strong>
        </nav>
        <h2>{{ selectedSet?.name || '评测集详情' }}</h2>
        <p>{{ selectedSet?.description || '维护该评测集的手工回归用例。' }}</p>
      </div>
      <div v-if="selectedSet" class="case-actions">
        <input
          ref="csvInput"
          data-testid="csv-import-input"
          class="csv-file-input"
          type="file"
          accept=".csv,text/csv"
          @change="importCsv"
        />
        <a-button data-testid="import-eval-cases" @click="openCsvImport">导入 CSV</a-button>
        <a-button data-testid="edit-eval-set-columns" @click="openFieldDialog">编辑列</a-button>
        <a-button
          data-testid="submit-eval-set-version"
          :disabled="versionState.submitDisabled || selectedSet.cases.length === 0"
          :loading="submittingVersion"
          @click="submitVersion"
        >
          提交新版本
        </a-button>
        <a-button type="primary" data-testid="add-eval-case" @click="openCreateCase">添加用例</a-button>
      </div>
    </header>

    <section v-if="selectedSet" class="detail-overview" data-testid="eval-set-detail-overview">
      <div class="overview-item">
        <span>状态</span>
        <div class="overview-value">
          <a-tag
            data-testid="eval-set-version-tag"
            :color="versionState.tone === 'version' ? 'success' : versionState.tone === 'dirty' ? 'warning' : 'default'"
          >
            {{ versionState.label }}
          </a-tag>
        </div>
      </div>
      <div class="overview-item">
        <span>版本</span>
        <strong>{{ selectedSet.versionCount || 0 }} 个版本</strong>
      </div>
      <div class="overview-item">
        <span>用例</span>
        <strong>{{ selectedSet.cases.length }} 条用例</strong>
      </div>
      <div class="overview-item overview-fields">
        <span>字段</span>
        <div class="overview-value" data-testid="eval-set-field-summary">
          <span v-for="field in fieldSchema" :key="field.key" class="field-summary-chip">
            {{ displayEvalSetFieldLabel(field) }}
          </span>
        </div>
      </div>
    </section>

    <a-tabs v-if="selectedSet" v-model:activeKey="detailTab" class="detail-tabs">
      <a-tab-pane key="cases">
        <template #tab>
          <span data-testid="eval-set-cases-tab">用例</span>
        </template>
      </a-tab-pane>
      <a-tab-pane key="experiments">
        <template #tab>
          <span data-testid="eval-set-related-tab">关联实验</span>
        </template>
      </a-tab-pane>
    </a-tabs>

    <template v-if="selectedSet && detailTab === 'cases'">
      <a-table
        v-if="selectedSet.cases.length > 0"
        row-key="id"
        :data-source="selectedSet.cases"
        bordered
        table-layout="auto"
        class="detail-table cases-table"
      >
        <a-table-column
          data-index="input"
          title="输入"
          class-name="case-input-column"
          header-class-name="case-input-column"
          ellipsis
        />
        <a-table-column
          data-index="expectedOutput"
          title="期望输出"
          class-name="case-expected-column"
          header-class-name="case-expected-column"
          ellipsis
        />
        <a-table-column
          v-for="field in dynamicFields"
          :key="field.key"
          :title="displayEvalSetFieldLabel(field)"
          class-name="case-dynamic-column"
          header-class-name="case-dynamic-column"
          ellipsis
        >
          <template #default="{ record: row }">
            {{ row.metadata?.[field.key] || '' }}
          </template>
        </a-table-column>
        <a-table-column title="标签" class-name="case-tags-column" header-class-name="case-tags-column">
          <template #default="{ record: row }">
            <a-tag v-for="tag in row.tags" :key="tag" size="small" class="tag-chip">
              {{ tag }}
            </a-tag>
            <span v-if="row.tags.length === 0" class="muted">无标签</span>
          </template>
        </a-table-column>
        <a-table-column title="操作" class-name="case-action-column" header-class-name="case-action-column">
          <template #default="{ record: row }">
            <a-button type="link" size="small" @click="openEditCase(row)">编辑用例</a-button>
            <a-button danger type="link" size="small" @click="deleteCase(row)">删除</a-button>
          </template>
        </a-table-column>
      </a-table>

      <div v-else class="case-empty">
        <h3>还没有用例</h3>
        <p>至少添加一条输入和期望输出，后续实验才能运行。</p>
      </div>

      <section class="version-records" data-testid="eval-set-version-records">
        <div class="version-records-header">
          <h4>版本记录</h4>
          <span>{{ versionRecords.length }} 条</span>
        </div>
        <article v-for="version in versionRecords" :key="version.id" class="version-record-row">
          <div>
            <strong>v{{ version.version }}</strong>
            <span>{{ version.description || '无描述' }}</span>
          </div>
          <em>{{ version.caseCount }} 条用例 · {{ version.createdAt }}</em>
        </article>
        <p v-if="versionRecords.length === 0" class="muted">暂无已提交版本</p>
      </section>
    </template>

    <section v-else-if="selectedSet" class="related-experiments" data-testid="related-experiments-panel">
      <a-table
        v-if="relatedExperiments.length > 0"
        row-key="id"
        :data-source="relatedExperiments"
        bordered
        table-layout="auto"
        class="detail-table related-experiments-table"
      >
        <a-table-column
          data-index="name"
          title="实验名称"
          class-name="related-name-column"
          header-class-name="related-name-column"
          ellipsis
        />
        <a-table-column title="版本" class-name="related-version-column" header-class-name="related-version-column">
          <template #default="{ record: row }">
            <a-tag>{{ describeRelated(row).versionText }}</a-tag>
          </template>
        </a-table-column>
        <a-table-column
          data-index="targetType"
          title="目标"
          class-name="related-target-column"
          header-class-name="related-target-column"
        />
        <a-table-column title="状态" class-name="related-status-column" header-class-name="related-status-column">
          <template #default="{ record: row }">
            <a-tag :color="relatedStatusColor(row)">{{ row.status }}</a-tag>
          </template>
        </a-table-column>
        <a-table-column title="最近运行" class-name="related-run-column" header-class-name="related-run-column">
          <template #default="{ record: row }">
            {{ describeRelated(row).runText }}
          </template>
        </a-table-column>
        <a-table-column title="分数" class-name="related-score-column" header-class-name="related-score-column">
          <template #default="{ record: row }">
            {{ row.latestRunScore === null ? '-' : row.latestRunScore.toFixed(2) }}
          </template>
        </a-table-column>
        <a-table-column
          data-index="createdAt"
          title="创建时间"
          class-name="related-created-column"
          header-class-name="related-created-column"
          ellipsis
        />
      </a-table>
      <div v-else class="case-empty">
        <h3>暂无关联实验</h3>
        <p>创建实验并选择该评测集版本后，会在这里看到关联关系。</p>
      </div>
    </section>

    <div v-else-if="!loading" class="case-empty">
      <h3>评测集不存在</h3>
      <p>返回评测集列表重新选择。</p>
    </div>

    <a-modal
      v-model:open="caseDialogVisible"
      :title="editingCase ? '编辑用例' : '添加用例'"
      width="35rem"
      :mask-closable="false"
      destroy-on-close
    >
      <a-form :label-col="{ style: { width: '5.75rem' } }">
        <a-form-item label="输入" required>
          <a-textarea v-model:value="caseForm.input" :rows="3" placeholder="用户输入或测试问题" />
        </a-form-item>
        <a-form-item label="期望输出" required>
          <a-textarea v-model:value="caseForm.expectedOutput" :rows="3" placeholder="期望回答包含的标准答案" />
        </a-form-item>
        <a-form-item label="标签">
          <a-input v-model:value="caseForm.tags" placeholder="用英文逗号分隔，如 refund,policy" />
        </a-form-item>
        <a-form-item
          v-for="field in dynamicFields"
          :key="field.key"
          :label="displayEvalSetFieldLabel(field)"
          :required="field.required"
        >
          <a-input
            v-model:value="caseForm.metadata[field.key]"
            :data-testid="`eval-case-field-${field.key}`"
            :placeholder="displayEvalSetFieldLabel(field)"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="caseDialogVisible = false">取消</a-button>
        <a-button type="primary" :loading="saving" data-testid="save-eval-case" @click="submitCase">确定</a-button>
      </template>
    </a-modal>

    <a-modal
      v-model:open="fieldDialogVisible"
      title="编辑列"
      width="42rem"
      :mask-closable="false"
      destroy-on-close
    >
      <div class="field-editor" data-testid="eval-set-field-editor">
        <div v-for="(field, index) in fieldDrafts" :key="`${field.key}-${index}`" class="field-editor-row">
          <a-input v-model:value="field.key" placeholder="字段键" :disabled="field.key === 'input' || field.key === 'expectedOutput'" />
          <a-input v-model:value="field.label" placeholder="字段名称" />
          <label class="field-required">
            <input v-model="field.required" type="checkbox" :disabled="field.key === 'input' || field.key === 'expectedOutput'" />
            必填
          </label>
        </div>
        <a-button data-testid="add-eval-set-field" @click="addFieldDraft">添加列</a-button>
      </div>
      <template #footer>
        <a-button @click="fieldDialogVisible = false">取消</a-button>
        <a-button type="primary" data-testid="save-eval-set-fields" :loading="saving" @click="saveFields">保存列</a-button>
      </template>
    </a-modal>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'

import {
  createEvalCase,
  deleteEvalCase,
  getEvalSet,
  importEvalCasesCsv,
  listEvalSetRelatedExperiments,
  listEvalSetVersions,
  submitEvalSetVersion,
  updateEvalCase,
  updateEvalSetFields,
  type EvalCase,
  type EvalSetDetail,
  type EvalSetField,
  type EvalSetRelatedExperiment,
  type EvalSetVersion,
} from '@/api/evaluation'
import {
  describeEvalSetVersionState,
  displayEvalSetFieldLabel,
  normalizeCaseTags,
  normalizeFieldDrafts,
} from './evalSetViewModel'
import { describeEvalSetRelatedExperiment } from './relatedExperimentsViewModel'
import { acceptedCsvName } from './csvToolsViewModel'

const route = useRoute()
const router = useRouter()

const selectedSet = ref<EvalSetDetail | null>(null)
const loading = ref(false)
const saving = ref(false)
const submittingVersion = ref(false)
const versionRecords = ref<EvalSetVersion[]>([])
const relatedExperiments = ref<EvalSetRelatedExperiment[]>([])
const fieldDialogVisible = ref(false)
const fieldDrafts = ref<EvalSetField[]>([])
const detailTab = ref<'cases' | 'experiments'>('cases')
const csvInput = ref<HTMLInputElement | null>(null)

const caseDialogVisible = ref(false)
const editingCase = ref<EvalCase | null>(null)
const caseForm = reactive<{ input: string; expectedOutput: string; tags: string; metadata: Record<string, string> }>({
  input: '',
  expectedOutput: '',
  tags: '',
  metadata: {},
})
const versionState = computed(() => selectedSet.value
  ? describeEvalSetVersionState(selectedSet.value)
  : describeEvalSetVersionState({ latestVersion: '', draftChanged: true }))
const fieldSchema = computed(() => selectedSet.value?.fieldSchema || [])
const dynamicFields = computed(() => fieldSchema.value.filter((field) => !['input', 'expectedOutput'].includes(field.key)))

onMounted(loadCurrentSet)
watch(() => route.params.id, loadCurrentSet)

async function loadCurrentSet() {
  const evalSetId = Number(route.params.id || 0)
  if (!evalSetId) {
    selectedSet.value = null
    return
  }
  loading.value = true
  try {
    selectedSet.value = await getEvalSet(evalSetId)
    detailTab.value = 'cases'
    await Promise.all([loadVersions(evalSetId), loadRelatedExperiments(evalSetId)])
  } finally {
    loading.value = false
  }
}

async function refreshCurrentSet() {
  if (!selectedSet.value) return
  const evalSetId = selectedSet.value.id
  selectedSet.value = await getEvalSet(evalSetId)
  await Promise.all([loadVersions(evalSetId), loadRelatedExperiments(evalSetId)])
}

async function loadVersions(evalSetId: number) {
  const result = await listEvalSetVersions(evalSetId)
  versionRecords.value = result.list
}

async function loadRelatedExperiments(evalSetId: number) {
  const result = await listEvalSetRelatedExperiments(evalSetId)
  relatedExperiments.value = result.list
}

function describeRelated(experiment: EvalSetRelatedExperiment) {
  return describeEvalSetRelatedExperiment(experiment)
}

function relatedStatusColor(experiment: EvalSetRelatedExperiment) {
  const tone = describeRelated(experiment).statusTone
  return tone === 'info' ? 'default' : tone
}

function openCreateCase() {
  editingCase.value = null
  caseForm.input = ''
  caseForm.expectedOutput = ''
  caseForm.tags = ''
  caseForm.metadata = Object.fromEntries(dynamicFields.value.map((field) => [field.key, '']))
  caseDialogVisible.value = true
}

function openEditCase(evalCase: EvalCase) {
  editingCase.value = evalCase
  caseForm.input = evalCase.input
  caseForm.expectedOutput = evalCase.expectedOutput
  caseForm.tags = evalCase.tags.join(', ')
  caseForm.metadata = Object.fromEntries(dynamicFields.value.map((field) => [field.key, String(evalCase.metadata?.[field.key] || '')]))
  caseDialogVisible.value = true
}

async function submitCase() {
  if (!selectedSet.value) return
  const input = caseForm.input.trim()
  const expectedOutput = caseForm.expectedOutput.trim()
  if (!input || !expectedOutput) {
    message.error('请输入用例输入和期望输出')
    return
  }
  saving.value = true
  try {
    const payload = {
      input,
      expectedOutput,
      tags: normalizeCaseTags(caseForm.tags.split(',')),
      metadata: Object.fromEntries(Object.entries(caseForm.metadata).filter(([, value]) => String(value || '').trim())),
    }
    if (editingCase.value) {
      await updateEvalCase(editingCase.value.id, payload)
      message.success('用例已保存')
    } else {
      await createEvalCase(selectedSet.value.id, payload)
      message.success('用例已添加')
    }
    caseDialogVisible.value = false
    await refreshCurrentSet()
  } finally {
    saving.value = false
  }
}

function openFieldDialog() {
  if (!selectedSet.value) return
  fieldDrafts.value = fieldSchema.value.map((field) => ({ ...field, label: displayEvalSetFieldLabel(field) }))
  fieldDialogVisible.value = true
}

function addFieldDraft() {
  fieldDrafts.value.push({
    key: '',
    label: '',
    contentType: 'TEXT',
    required: false,
    displayOrder: fieldDrafts.value.length + 1,
  })
}

async function saveFields() {
  if (!selectedSet.value) return
  const fields = normalizeFieldDrafts(fieldDrafts.value)
  saving.value = true
  try {
    await updateEvalSetFields(selectedSet.value.id, fields)
    message.success('列配置已保存')
    fieldDialogVisible.value = false
    await refreshCurrentSet()
  } finally {
    saving.value = false
  }
}

async function submitVersion() {
  if (!selectedSet.value || versionState.value.submitDisabled || selectedSet.value.cases.length === 0) return
  submittingVersion.value = true
  try {
    const version = await submitEvalSetVersion(selectedSet.value.id, { description: '从评测工作台提交' })
    message.success(`已提交版本 v${version.version}`)
    await refreshCurrentSet()
  } finally {
    submittingVersion.value = false
  }
}

function deleteCase(evalCase: EvalCase) {
  Modal.confirm({
    title: '提示',
    content: '确定删除该用例？',
    okText: '确定',
    cancelText: '取消',
    okType: 'danger',
    onOk: async () => {
      await deleteEvalCase(evalCase.id)
      message.success('用例已删除')
      await refreshCurrentSet()
    },
  })
}

function openCsvImport() {
  csvInput.value?.click()
}

async function importCsv(event: Event) {
  if (!selectedSet.value) return
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!acceptedCsvName(file.name)) {
    message.error('请选择 CSV 文件')
    input.value = ''
    return
  }
  const result = await importEvalCasesCsv(selectedSet.value.id, file)
  message.success(`已导入 ${result.createdCount} 条用例`)
  await refreshCurrentSet()
  input.value = ''
}
</script>

<style scoped>
.eval-set-detail-page {
  min-height: calc(100vh - 7rem);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  margin-bottom: 0.875rem;
}

.detail-title-block {
  min-width: 0;
  flex: 1;
}

.detail-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: 0.75rem;
  padding: 0.75rem 0;
  margin-bottom: 0.875rem;
  border-bottom: 0.0625rem solid var(--color-border-default);
}

.overview-item {
  display: grid;
  gap: 0.375rem;
  align-content: start;
  min-width: 0;
}

.overview-item > span {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.overview-item strong {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: 600;
}

.overview-fields {
  grid-column: span 2;
}

.overview-value {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.375rem;
  min-width: 0;
}

.detail-breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.375rem;
  margin-bottom: 0.5rem;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.detail-breadcrumb button {
  border: 0;
  padding: 0;
  color: var(--color-primary);
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.detail-breadcrumb strong {
  max-width: min(40rem, 100%);
  overflow: hidden;
  color: var(--color-text-primary);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-header h2,
.case-empty h3 {
  margin: 0 0 0.375rem;
  color: var(--color-text-primary);
}

.detail-header h2 {
  font-size: var(--text-xl);
}

.detail-header p,
.case-empty p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.55;
}

.field-summary-chip {
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-sm);
  padding: 0.125rem 0.5rem;
  background: var(--color-bg-page);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
}

.case-actions {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.csv-file-input {
  position: absolute;
  width: 0.0625rem;
  height: 0.0625rem;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
}

@media (max-width: 48rem) {
  .detail-header {
    flex-direction: column;
  }

  .case-actions {
    justify-content: flex-start;
    width: 100%;
  }

  .overview-fields {
    grid-column: span 1;
  }
}

.detail-tabs {
  margin-bottom: var(--space-3);
}

.detail-table {
  width: 100%;
}

.detail-table :deep(.cell) {
  line-height: 1.45;
}

.detail-table :deep(.ant-table-cell) {
  overflow-wrap: normal;
  word-break: normal;
}

.cases-table :deep(.case-input-column),
.cases-table :deep(.case-expected-column) {
  min-width: 14rem;
  width: 30%;
}

.cases-table :deep(.case-dynamic-column) {
  min-width: 10rem;
}

.cases-table :deep(.case-tags-column) {
  min-width: 10rem;
  width: 12rem;
}

.cases-table :deep(.case-action-column) {
  min-width: 9rem;
  width: 9rem;
}

.related-experiments-table :deep(.related-name-column) {
  min-width: 18rem;
  width: 34%;
}

.related-experiments-table :deep(.related-version-column) {
  min-width: 7rem;
  width: 7rem;
}

.related-experiments-table :deep(.related-target-column) {
  min-width: 8rem;
  width: 8rem;
}

.related-experiments-table :deep(.related-status-column) {
  min-width: 7rem;
  width: 7rem;
}

.related-experiments-table :deep(.related-run-column) {
  min-width: 8rem;
  width: 8rem;
}

.related-experiments-table :deep(.related-score-column) {
  min-width: 6rem;
  width: 6rem;
}

.related-experiments-table :deep(.related-created-column) {
  min-width: 17rem;
  width: 20%;
}

.related-experiments-table :deep(.related-version-column .cell),
.related-experiments-table :deep(.related-target-column .cell),
.related-experiments-table :deep(.related-status-column .cell),
.related-experiments-table :deep(.related-run-column .cell),
.related-experiments-table :deep(.related-score-column .cell) {
  white-space: nowrap;
}

.tag-chip {
  margin-right: 0.375rem;
}

.muted {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.case-empty {
  min-height: 10rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-bottom: 0.0625rem solid var(--color-border-default);
}

.version-records {
  margin-top: 1rem;
  padding-top: 0.875rem;
  border-top: 0.0625rem solid var(--color-border-default);
}

.related-experiments {
  min-height: 10rem;
}

.version-records-header,
.version-record-row {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
}

.version-records-header {
  align-items: center;
  margin-bottom: 0.625rem;
}

.version-records-header h4 {
  margin: 0;
}

.version-record-row {
  align-items: center;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-sm);
  padding: 0.625rem;
  background: #fff;
}

.version-record-row + .version-record-row {
  margin-top: 0.5rem;
}

.version-record-row div {
  display: grid;
  gap: 0.125rem;
}

.version-record-row span,
.version-record-row em {
  color: var(--color-text-secondary);
  font-style: normal;
}

.field-editor {
  display: grid;
  gap: 0.625rem;
}

.field-editor-row {
  display: grid;
  grid-template-columns: minmax(9rem, 1fr) minmax(11rem, 1.2fr) 5rem;
  gap: 0.625rem;
  align-items: center;
}

.field-required {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}
</style>
