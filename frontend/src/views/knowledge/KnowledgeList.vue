<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-left">
        <div class="page-title">知识库管理</div>
        <div class="page-desc">沉淀业务资料，上传后自动整理成可回答内容</div>
      </div>
      <div class="page-header-actions">
        <a-input
          v-model:value="searchName"
          placeholder="搜索知识库名称"
          allow-clear
          class="kb-search-input"
          @input="onSearch"
        />
        <button class="btn-primary" @click="openCreate">
          <span class="button-icon"><PlusOutlined /></span>
          新建知识库
        </button>
      </div>
    </div>

    <div class="kb-grid">
      <div
        v-for="kb in kbList"
        :key="kb.id"
        class="kb-card"
        @click="goDocuments(kb.id)"
      >
        <div class="kb-card-header">
          <div class="kb-icon">
            <span class="kb-folder-icon"><FolderOutlined /></span>
          </div>
          <div class="kb-actions" @click.stop>
            <a-tag :color="kb.enabled ? 'success' : 'default'" class="kb-status-tag hify-tag">
              {{ kb.enabled ? '启用' : '禁用' }}
            </a-tag>
            <a-button type="link" size="small" @click="openEdit(kb)">编辑</a-button>
            <a-button type="link" danger size="small" @click="onDelete(kb)">删除</a-button>
          </div>
        </div>
        <div class="kb-name">{{ kb.name }}</div>
        <div class="kb-desc">{{ kb.description || '暂无描述' }}</div>
        <div class="kb-footer">
          <span class="kb-time">{{ formatDate(kb.createdAt) }}</span>
          <span class="kb-link">查看文档 →</span>
        </div>
      </div>

      <div v-if="kbList.length === 0 && !loading" class="kb-empty">
        <a-empty description="还没有知识库，点击「新建知识库」开始" />
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="page-pagination">
      <a-pagination
        v-model:current="page"
        :page-size="pageSize"
        :total="total"
        show-less-items
        @change="loadList"
      />
    </div>

    <!-- 新建/编辑弹窗 -->
    <a-modal
      v-model:open="dialogVisible"
      :title="editingKb ? '编辑知识库' : '新建知识库'"
      :width="kbDialogWidth"
      :mask-closable="false"
      destroy-on-close
    >
      <a-form ref="formRef" :model="form" :rules="rules" :label-col="{ style: { width: kbDialogLabelWidth } }">
        <a-form-item label="名称" name="name">
          <a-input v-model:value="form.name" placeholder="请输入知识库名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="3" placeholder="可选" />
        </a-form-item>
        <a-form-item v-if="editingKb" label="状态">
          <a-switch v-model:checked="form.enabled" :checked-value="1" :un-checked-value="0" />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="dialogVisible = false">取消</a-button>
        <a-button type="primary" :loading="saving" @click="onSubmit">确定</a-button>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import { FolderOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { notifySuccess } from '@/utils/notify'
import { listKb, createKb, updateKb, deleteKb } from '@/api/knowledge'
import type { KnowledgeBase } from '@/api/knowledge'

type FormRules = Record<string, unknown>
type FormInstance = {
  validate: () => Promise<unknown>
}

const router = useRouter()

const kbList = ref<KnowledgeBase[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 12
const searchName = ref('')
const kbDialogWidth = '27.5rem'
const kbDialogLabelWidth = '5rem'

const dialogVisible = ref(false)
const saving = ref(false)
const editingKb = ref<KnowledgeBase | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '', enabled: 1 as number })

const rules: FormRules = {
  name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }],
}

onMounted(loadList)

async function loadList() {
  loading.value = true
  try {
    const res = await listKb({ page: page.value, pageSize, name: searchName.value || undefined })
    kbList.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout>
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; loadList() }, 300)
}

function openCreate() {
  editingKb.value = null
  form.name = ''
  form.description = ''
  form.enabled = 1
  dialogVisible.value = true
}

function openEdit(kb: KnowledgeBase) {
  editingKb.value = kb
  form.name = kb.name
  form.description = kb.description
  form.enabled = kb.enabled
  dialogVisible.value = true
}

async function onSubmit() {
  await formRef.value?.validate()
  saving.value = true
  try {
    if (editingKb.value) {
      await updateKb(editingKb.value.id, { name: form.name, description: form.description, enabled: form.enabled })
      notifySuccess('保存成功')
    } else {
      await createKb({ name: form.name, description: form.description })
      notifySuccess('创建成功')
    }
    dialogVisible.value = false
    loadList()
  } finally {
    saving.value = false
  }
}

async function onDelete(kb: KnowledgeBase) {
  Modal.confirm({
    title: '提示',
    content: `确定删除知识库「${kb.name}」及其所有文档？`,
    okText: '确认',
    cancelText: '取消',
    onOk: async () => {
      await deleteKb(kb.id)
      notifySuccess('删除成功')
      await loadList()
    },
  })
}

function goDocuments(kbId: number) {
  router.push({ name: 'HifyKnowledgeDocuments', params: { kbId } })
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.page-header { margin-bottom: var(--space-5); }

.kb-search-input {
  width: 12.5rem;
  margin-right: 0.625rem;
}

.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(17.5rem, 1fr));
  gap: var(--space-4);
}

.kb-card {
  background: var(--color-bg-card, #fff);
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
  border-radius: 0.625rem;
  padding: var(--space-5);
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s, transform 0.15s;
}
.kb-card:hover {
  box-shadow: 0 0.25rem 1rem rgba(99,102,241,0.12);
  border-color: var(--color-primary-300, #a5b4fc);
  transform: translateY(-0.125rem);
}

.kb-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}
.kb-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary-500, #6366f1);
}
.kb-folder-icon {
  font-size: 1.375rem;
  display: inline-flex;
}
.button-icon { display: inline-flex; }
.kb-actions { display: flex; align-items: center; gap: var(--radius-xs); }
.kb-status-tag {
  margin-right: 0.375rem;
}

.kb-name {
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--color-text-primary, #0f1117);
  margin-bottom: 0.375rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.kb-desc {
  font-size: var(--text-sm);
  color: var(--color-text-secondary, #4b5268);
  line-height: 1.5;
  height: 2.5rem;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.kb-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.875rem;
  padding-top: var(--space-3);
  border-top: 0.0625rem solid var(--color-border-default, #e3e6ef);
}
.kb-time { font-size: var(--text-xs); color: var(--color-text-tertiary, #8b92a8); }
.kb-link { font-size: var(--text-xs); color: var(--color-primary-500, #6366f1); }

.kb-empty { grid-column: 1 / -1; padding: 3.75rem 0; }

.page-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-5);
}
</style>
