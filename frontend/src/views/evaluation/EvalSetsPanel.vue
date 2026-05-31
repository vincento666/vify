<template>
  <section class="eval-sets-panel">
    <div class="panel-toolbar">
      <el-input
        v-model="searchName"
        placeholder="搜索评测集"
        clearable
        class="search-input"
        @input="onSearch"
      />
      <el-button type="primary" data-testid="create-eval-set" @click="openCreateSet">
        创建评测集
      </el-button>
    </div>

    <div v-if="evalSets.length === 0 && !loading" class="empty-panel compact">
      <h3>整理回归用例</h3>
      <p>手动添加输入、期望输出和标签，先形成最小可重复评测集。</p>
      <el-button type="primary" @click="openCreateSet">创建评测集</el-button>
    </div>

    <div v-else class="eval-set-grid">
      <article
        v-for="evalSet in evalSets"
        :key="evalSet.id"
        class="eval-set-card"
        :class="{ selected: selectedSet?.id === evalSet.id }"
        @click="selectSet(evalSet)"
      >
        <div class="card-main">
          <h4>{{ evalSet.name }}</h4>
          <p>{{ evalSet.description || '暂无描述' }}</p>
        </div>
        <div class="card-footer">
          <el-tag :type="describeEvalSetCard(evalSet).tone === 'ready' ? 'success' : 'info'" effect="plain">
            {{ describeEvalSetCard(evalSet).caseCountText }}
          </el-tag>
          <div class="card-actions" @click.stop>
            <el-button type="primary" link size="small" @click="openCreateCase(evalSet)">添加用例</el-button>
            <el-button link size="small" @click="openEditSet(evalSet)">编辑</el-button>
            <el-button type="danger" link size="small" @click="deleteSet(evalSet)">删除</el-button>
          </div>
        </div>
      </article>
    </div>

    <section v-if="selectedSet" class="case-panel">
      <div class="case-panel-header">
        <div>
          <h3>{{ selectedSet.name }}</h3>
          <p>维护该评测集的手工回归用例。</p>
          <p class="csv-hint">{{ csvImportHint() }}</p>
        </div>
        <div class="case-actions">
          <input data-testid="csv-import-input" type="file" accept=".csv,text/csv" @change="importCsv" />
          <el-button type="primary" @click="openCreateCase(selectedSet)">添加用例</el-button>
        </div>
      </div>

      <el-table v-if="selectedSet.cases.length > 0" :data="selectedSet.cases" border>
        <el-table-column prop="input" label="输入" min-width="220" show-overflow-tooltip />
        <el-table-column prop="expectedOutput" label="期望输出" min-width="220" show-overflow-tooltip />
        <el-table-column label="标签" width="220">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" effect="plain" class="tag-chip">
              {{ tag }}
            </el-tag>
            <span v-if="row.tags.length === 0" class="muted">无标签</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link size="small" @click="openEditCase(row)">编辑用例</el-button>
            <el-button type="danger" link size="small" @click="deleteCase(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="case-empty">
        <h3>还没有用例</h3>
        <p>至少添加一条输入和期望输出，后续实验才能运行。</p>
      </div>
    </section>

    <el-dialog
      v-model="setDialogVisible"
      :title="editingSet ? '编辑评测集' : '创建评测集'"
      width="440px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form label-width="84px">
        <el-form-item label="名称" required>
          <el-input v-model="setForm.name" placeholder="请输入评测集名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="setForm.description" type="textarea" :rows="3" placeholder="描述适用场景" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="setDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-testid="save-eval-set" @click="submitSet">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="caseDialogVisible"
      :title="editingCase ? '编辑用例' : '添加用例'"
      width="560px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form label-width="92px">
        <el-form-item label="输入" required>
          <el-input v-model="caseForm.input" type="textarea" :rows="3" placeholder="用户输入或测试问题" />
        </el-form-item>
        <el-form-item label="期望输出" required>
          <el-input v-model="caseForm.expectedOutput" type="textarea" :rows="3" placeholder="期望回答包含的标准答案" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="caseForm.tags" placeholder="用英文逗号分隔，如 refund,policy" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="caseDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-testid="save-eval-case" @click="submitCase">确定</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  createEvalCase,
  createEvalSet,
  deleteEvalCase,
  deleteEvalSet,
  getEvalSet,
  importEvalCasesCsv,
  listEvalSets,
  updateEvalCase,
  updateEvalSet,
  type EvalCase,
  type EvalSet,
  type EvalSetDetail,
} from '@/api/evaluation'
import { describeEvalSetCard, normalizeCaseTags } from './evalSetViewModel'
import { acceptedCsvName, csvImportHint } from './csvToolsViewModel'

const evalSets = ref<EvalSet[]>([])
const selectedSet = ref<EvalSetDetail | null>(null)
const loading = ref(false)
const saving = ref(false)
const searchName = ref('')
const pageSize = 20

const setDialogVisible = ref(false)
const editingSet = ref<EvalSet | null>(null)
const setForm = reactive({ name: '', description: '' })

const caseDialogVisible = ref(false)
const editingCase = ref<EvalCase | null>(null)
const caseTargetSet = ref<EvalSet | EvalSetDetail | null>(null)
const caseForm = reactive({ input: '', expectedOutput: '', tags: '' })

onMounted(loadEvalSets)

async function loadEvalSets(selectId?: number) {
  loading.value = true
  try {
    const result = await listEvalSets({ page: 1, pageSize, name: searchName.value || undefined })
    evalSets.value = result.list
    const targetId = selectId || selectedSet.value?.id
    if (targetId && evalSets.value.some((item) => item.id === targetId)) {
      selectedSet.value = await getEvalSet(targetId)
    } else if (!targetId) {
      selectedSet.value = null
    }
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout>
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    selectedSet.value = null
    loadEvalSets()
  }, 300)
}

async function selectSet(evalSet: EvalSet) {
  selectedSet.value = await getEvalSet(evalSet.id)
}

function openCreateSet() {
  editingSet.value = null
  setForm.name = ''
  setForm.description = ''
  setDialogVisible.value = true
}

function openEditSet(evalSet: EvalSet) {
  editingSet.value = evalSet
  setForm.name = evalSet.name
  setForm.description = evalSet.description
  setDialogVisible.value = true
}

async function submitSet() {
  const name = setForm.name.trim()
  if (!name) {
    ElMessage.error('请输入评测集名称')
    return
  }
  saving.value = true
  try {
    const saved = editingSet.value
      ? await updateEvalSet(editingSet.value.id, { name, description: setForm.description })
      : await createEvalSet({ name, description: setForm.description })
    ElMessage.success(editingSet.value ? '保存成功' : '创建成功')
    setDialogVisible.value = false
    await loadEvalSets(saved.id)
  } finally {
    saving.value = false
  }
}

function openCreateCase(evalSet: EvalSet | EvalSetDetail) {
  caseTargetSet.value = evalSet
  editingCase.value = null
  caseForm.input = ''
  caseForm.expectedOutput = ''
  caseForm.tags = ''
  caseDialogVisible.value = true
}

function openEditCase(evalCase: EvalCase) {
  if (!selectedSet.value) return
  caseTargetSet.value = selectedSet.value
  editingCase.value = evalCase
  caseForm.input = evalCase.input
  caseForm.expectedOutput = evalCase.expectedOutput
  caseForm.tags = evalCase.tags.join(', ')
  caseDialogVisible.value = true
}

async function submitCase() {
  if (!caseTargetSet.value) return
  const input = caseForm.input.trim()
  const expectedOutput = caseForm.expectedOutput.trim()
  if (!input || !expectedOutput) {
    ElMessage.error('请输入用例输入和期望输出')
    return
  }
  saving.value = true
  try {
    const payload = {
      input,
      expectedOutput,
      tags: normalizeCaseTags(caseForm.tags.split(',')),
      metadata: {},
    }
    if (editingCase.value) {
      await updateEvalCase(editingCase.value.id, payload)
      ElMessage.success('用例已保存')
    } else {
      await createEvalCase(caseTargetSet.value.id, payload)
      ElMessage.success('用例已添加')
    }
    caseDialogVisible.value = false
    await loadEvalSets(caseTargetSet.value.id)
  } finally {
    saving.value = false
  }
}

async function deleteSet(evalSet: EvalSet) {
  try {
    await ElMessageBox.confirm(`确定删除评测集「${evalSet.name}」及其用例？`, '提示', { type: 'warning' })
    await deleteEvalSet(evalSet.id)
    ElMessage.success('删除成功')
    if (selectedSet.value?.id === evalSet.id) selectedSet.value = null
    await loadEvalSets()
  } catch { /* cancel */ }
}

async function deleteCase(evalCase: EvalCase) {
  try {
    await ElMessageBox.confirm('确定删除该用例？', '提示', { type: 'warning' })
    await deleteEvalCase(evalCase.id)
    ElMessage.success('用例已删除')
    if (selectedSet.value) await loadEvalSets(selectedSet.value.id)
  } catch { /* cancel */ }
}

async function importCsv(event: Event) {
  if (!selectedSet.value) return
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!acceptedCsvName(file.name)) {
    ElMessage.error('请选择 CSV 文件')
    input.value = ''
    return
  }
  const result = await importEvalCasesCsv(selectedSet.value.id, file)
  ElMessage.success(`已导入 ${result.createdCount} 条用例`)
  await loadEvalSets(selectedSet.value.id)
  input.value = ''
}
</script>

<style scoped>
.eval-sets-panel {
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

.eval-set-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.eval-set-card {
  min-height: 136px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 14px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.eval-set-card:hover,
.eval-set-card.selected {
  border-color: var(--el-color-primary);
  box-shadow: 0 6px 20px rgba(31, 43, 76, 0.08);
}

.card-main h4,
.case-panel h3,
.case-empty h3 {
  margin: 0 0 6px;
  color: var(--el-text-color-primary);
  font-size: 15px;
}

.card-main p,
.case-panel p,
.case-empty p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.55;
}

.card-footer,
.case-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.case-panel {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.case-panel-header {
  margin-bottom: 12px;
}

.case-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.case-actions input {
  max-width: 220px;
  color: var(--el-text-color-secondary);
}

.csv-hint {
  margin-top: 4px;
}

.tag-chip {
  margin-right: 6px;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.case-empty {
  min-height: 160px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.compact {
  min-height: 220px;
}
</style>
