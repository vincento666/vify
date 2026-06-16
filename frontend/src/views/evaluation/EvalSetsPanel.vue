<template>
  <section class="eval-sets-panel">
    <div class="panel-toolbar">
      <a-input
        v-model:value="searchName"
        placeholder="搜索评测集" allow-clear
        class="search-input"
        @input="onSearch"
      />
      <a-button type="primary" data-testid="create-eval-set" @click="openCreateSet">
        创建评测集
      </a-button>
    </div>

    <div v-if="evalSets.length === 0 && !loading" class="empty-panel compact">
      <h3>整理回归用例</h3>
      <p>手动添加输入、期望输出和标签，先形成最小可重复评测集。</p>
      <a-button type="primary" @click="openCreateSet">创建评测集</a-button>
    </div>

    <div v-else class="eval-set-grid">
      <article v-for="evalSet in evalSets" :key="evalSet.id" class="eval-set-card">
        <div class="card-main">
          <h4>{{ evalSet.name }}</h4>
          <p>{{ evalSet.description || '暂无描述' }}</p>
        </div>
        <div class="card-footer">
          <a-tag :color="describeEvalSetCard(evalSet).tone === 'ready' ? 'success' : 'default'">
            {{ describeEvalSetCard(evalSet).caseCountText }}
          </a-tag>
          <div class="card-actions">
            <a-button
              type="link"
              size="small"
              data-testid="view-eval-set-detail"
              @click="openDetail(evalSet)"
            >
              查看详情
            </a-button>
            <a-button type="link" size="small" @click="openEditSet(evalSet)">编辑</a-button>
            <a-button danger type="link" size="small" @click="deleteSet(evalSet)">删除</a-button>
          </div>
        </div>
      </article>
    </div>

    <a-modal
      v-model:open="setDialogVisible"
      :title="editingSet ? '编辑评测集' : '创建评测集'"
      width="27.5rem"
      :mask-closable="false"
      destroy-on-close
    >
      <a-form :label-col="{ style: { width: '5.25rem' } }">
        <a-form-item label="名称" required>
          <a-input v-model:value="setForm.name" placeholder="请输入评测集名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="setForm.description" :rows="3" placeholder="描述适用场景" />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="setDialogVisible = false">取消</a-button>
        <a-button type="primary" :loading="saving" data-testid="save-eval-set" @click="submitSet">确定</a-button>
      </template>
    </a-modal>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'

import {
  createEvalSet,
  deleteEvalSet,
  listEvalSets,
  updateEvalSet,
  type EvalSet,
} from '@/api/evaluation'
import { describeEvalSetCard } from './evalSetViewModel'

const router = useRouter()

const evalSets = ref<EvalSet[]>([])
const loading = ref(false)
const saving = ref(false)
const searchName = ref('')
const pageSize = 20

const setDialogVisible = ref(false)
const editingSet = ref<EvalSet | null>(null)
const setForm = reactive({ name: '', description: '' })

onMounted(loadEvalSets)

async function loadEvalSets() {
  loading.value = true
  try {
    const result = await listEvalSets({ page: 1, pageSize, name: searchName.value || undefined })
    evalSets.value = result.list
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout>
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadEvalSets, 300)
}

function openDetail(evalSet: EvalSet) {
  router.push({ name: 'HifyEvaluationEvalSets', params: { id: evalSet.id } })
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
    message.error('请输入评测集名称')
    return
  }
  saving.value = true
  try {
    const saved = editingSet.value
      ? await updateEvalSet(editingSet.value.id, { name, description: setForm.description })
      : await createEvalSet({ name, description: setForm.description })
    message.success(editingSet.value ? '保存成功' : '创建成功')
    setDialogVisible.value = false
    if (editingSet.value) {
      await loadEvalSets()
    } else {
      router.push({ name: 'HifyEvaluationEvalSets', params: { id: saved.id } })
    }
  } finally {
    saving.value = false
  }
}

function deleteSet(evalSet: EvalSet) {
  Modal.confirm({
    title: '提示',
    content: `确定删除评测集「${evalSet.name}」及其用例？`,
    okText: '确定',
    cancelText: '取消',
    okType: 'danger',
    onOk: async () => {
      await deleteEvalSet(evalSet.id)
      message.success('删除成功')
      await loadEvalSets()
    },
  })
}
</script>

<style scoped>
.eval-sets-panel {
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

.eval-set-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(17.5rem, 1fr));
  gap: var(--space-3);
}

.eval-set-card {
  min-height: 8.5rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border: 0.0625rem solid var(--color-border-default);
  border-radius: var(--radius-md);
  padding: 0.875rem;
  background: #fff;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.eval-set-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 0.375rem 1.25rem rgba(31, 43, 76, 0.08);
}

.card-main h4 {
  margin: 0 0 0.375rem;
  color: var(--color-text-primary);
  font-size: var(--text-base);
}

.card-main p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.55;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 0.125rem;
}

.compact {
  min-height: 13.75rem;
}
</style>
