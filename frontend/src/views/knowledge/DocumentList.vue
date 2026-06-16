<template>
  <div class="page-container">
    <!-- 顶部 -->
    <div class="page-header">
      <div class="page-header-left">
        <a-button type="link" class="back-button" @click="router.push({ name: 'HifyKnowledge' })">
          <span class="button-icon"><ArrowLeftOutlined /></span>
        </a-button>
        <div>
          <div class="page-title">{{ kbName || '知识库文档' }}</div>
          <div class="page-desc">管理文档与 FAQ，上传后自动分块并生成检索索引</div>
        </div>
      </div>
      <div class="page-header-actions">
        <a-button v-if="activeTab === 'documents'" type="primary" @click="uploadVisible = true">
          <span class="button-icon"><UploadOutlined /></span>
          上传文档
        </a-button>
        <template v-else-if="activeTab === 'faqs'">
          <a-button @click="openFaqImport">
            <span class="button-icon"><UploadOutlined /></span>
            导入 CSV
          </a-button>
          <a-button @click="downloadFaqCsv">
            <span class="button-icon"><DownloadOutlined /></span>
            导出 CSV
          </a-button>
          <a-button type="primary" @click="openCreateFaq">
            <span class="button-icon"><PlusOutlined /></span>
            新增 FAQ
          </a-button>
        </template>
      </div>
    </div>

    <div class="knowledge-lifecycle" aria-label="知识库生命周期">
      <div v-for="(step, index) in knowledgeLifecycleSteps" :key="step" class="knowledge-lifecycle-step">
        <span class="knowledge-lifecycle-index">{{ index + 1 }}</span>
        <span>{{ step }}</span>
      </div>
    </div>

    <div class="hify-card">
      <a-tabs v-model:activeKey="activeTab" class="kb-tabs" @change="onTabChange">
        <a-tab-pane key="documents" tab="文档">
          <div v-if="docList.length > 0" class="knowledge-table-shell">
            <div class="knowledge-table document-table" role="table" aria-label="知识库文档">
              <div class="knowledge-table-row knowledge-table-head" role="row">
                <div role="columnheader">文件名</div>
                <div role="columnheader">类型</div>
                <div role="columnheader">大小</div>
                <div role="columnheader">分块数</div>
                <div role="columnheader">状态</div>
                <div role="columnheader">上传时间</div>
                <div role="columnheader">操作</div>
              </div>
              <div v-for="row in docList" :key="row.id" class="knowledge-table-row" role="row">
                <div class="doc-name" role="cell">
                  <span class="doc-icon"><FileTextOutlined /></span>
                  <span>{{ row.name }}</span>
                </div>
                <div role="cell">
                  <a-tag class="hify-tag">{{ row.fileType.toUpperCase() }}</a-tag>
                </div>
                <div role="cell">{{ formatSize(row.fileSize) }}</div>
                <div role="cell">
                  <span v-if="row.status === 'DONE'" class="chunk-count">{{ row.chunkCount }}</span>
                  <span v-else class="text-muted">—</span>
                </div>
                <div role="cell">
                  <div class="status-cell">
                    <a-tag :color="statusType(row.status)" class="hify-tag">
                      <span v-if="row.status === 'PROCESSING'" class="rotating inline-icon"><LoadingOutlined /></span>
                      {{ statusLabel(row.status) }}
                    </a-tag>
                    <a-tooltip v-if="row.status === 'FAILED' && row.errorMessage" :title="row.errorMessage" placement="top">
                      <span class="error-icon"><WarningOutlined /></span>
                    </a-tooltip>
                  </div>
                </div>
                <div role="cell">{{ formatTime(row.createdAt) }}</div>
                <div class="document-action-cell table-actions" role="cell">
                  <a-button
                    type="link" size="small"
                    :disabled="row.status !== 'DONE'"
                    @click="viewChunks(row)"
                  >查看分块</a-button>
                  <a-button
                    type="link" danger size="small"
                    :disabled="row.status === 'PROCESSING'"
                    @click="onDelete(row)"
                  >删除</a-button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="docList.length === 0" class="table-empty">
            <a-empty description="暂无文档，点击「上传文档」开始" />
          </div>
        </a-tab-pane>

        <a-tab-pane key="faqs" tab="FAQ">
          <input ref="faqCsvInputRef" class="hidden-input" type="file" accept=".csv,text/csv" @change="onFaqCsvSelected">
          <div v-if="faqList.length > 0" class="knowledge-table-shell">
            <div class="knowledge-table faq-table" data-testid="faq-table" role="table" aria-label="知识库 FAQ">
              <div class="knowledge-table-row knowledge-table-head" role="row">
                <div role="columnheader">问题</div>
                <div role="columnheader">答案</div>
                <div role="columnheader">关键词</div>
                <div role="columnheader">分类</div>
                <div role="columnheader">优先级</div>
                <div role="columnheader">状态</div>
                <div role="columnheader">操作</div>
              </div>
              <div v-for="row in faqList" :key="row.id" class="knowledge-table-row" role="row">
                <div role="cell">
                  <div class="faq-question">{{ row.question }}</div>
                  <div class="faq-subline">{{ row.alternativeQuestions.join(' / ') || '无相似问法' }}</div>
                </div>
                <div role="cell">
                  <div class="faq-answer">{{ row.answer }}</div>
                </div>
                <div role="cell">
                  <div class="tag-list">
                    <a-tag v-for="keyword in row.keywords" :key="keyword" class="hify-tag">{{ keyword }}</a-tag>
                    <span v-if="row.keywords.length === 0" class="text-muted">—</span>
                  </div>
                </div>
                <div role="cell">{{ row.category || '默认' }}</div>
                <div role="cell">{{ row.priority }}</div>
                <div role="cell">
                  <a-tag :color="row.enabled ? 'success' : 'default'" class="hify-tag">{{ row.enabled ? '启用' : '停用' }}</a-tag>
                </div>
                <div class="faq-action-cell table-actions" role="cell">
                  <a-button type="link" size="small" @click="openEditFaq(row)">
                    <span class="button-icon"><EditOutlined /></span>
                    编辑
                  </a-button>
                  <a-button type="link" danger size="small" @click="onDeleteFaq(row)">
                    <span class="button-icon"><DeleteOutlined /></span>
                    删除
                  </a-button>
                </div>
              </div>
            </div>
          </div>
          <div v-if="faqList.length === 0" class="table-empty">
            <a-empty description="暂无 FAQ" />
          </div>
        </a-tab-pane>

        <a-tab-pane key="retrieval" tab="检索测试">
          <div class="retrieval-panel" data-testid="retrieval-test-panel">
            <div class="retrieval-form">
              <div class="retrieval-toolbar">
                <a-input
                  v-model:value="retrievalQuery"
                  class="retrieval-query-input"
                  data-testid="retrieval-query-input"
                  placeholder="输入用户问题，检查会命中哪些内容"
                  allow-clear
                  @keyup.enter="runRetrievalTest"
                />
                <a-select v-model:value="retrievalMode" class="retrieval-mode-select" aria-label="检索方式" placeholder="检索方式" :options="retrievalModeOptions" />
                <a-input-number
                  v-model:value="retrievalTopK"
                  class="retrieval-topk-input"
                  :min="1"
                  :max="10"
                />
                <a-button class="retrieval-advanced-button" @click="retrievalAdvancedOpen = !retrievalAdvancedOpen">
                  <span class="button-icon"><SettingOutlined /></span>
                  高级设置
                </a-button>
                <a-button class="retrieval-search-button" type="primary" :loading="retrievalLoading" @click="runRetrievalTest">
                  <span class="button-icon"><SearchOutlined /></span>
                  测试检索
                </a-button>
              </div>
              <div v-if="retrievalAdvancedOpen" class="retrieval-advanced">
                <a-form-item label="最低命中分">
                  <a-input-number
                    v-model:value="retrievalScoreThreshold"
                    :min="0"
                    :max="1"
                    :step="0.05"
                  />
                </a-form-item>
                <a-form-item label="结果重排">
                  <a-switch v-model:checked="retrievalRerank" checked-children="开启" un-checked-children="关闭" />
                </a-form-item>
              </div>
            </div>
            <div class="retrieval-results">
              <div v-for="hit in retrievalHits" :key="`${hit.sourceType}-${hit.faqId || hit.chunkId}-${hit.matchType}`" class="retrieval-hit">
                <div class="retrieval-hit-header">
                  <div>
                    <a-tag :color="hit.sourceType === 'FAQ' ? 'success' : 'processing'" class="hify-tag">{{ sourceLabel(hit.sourceType) }}</a-tag>
                    <a-tag class="hify-tag">{{ matchTypeLabel(hit.matchType) }}</a-tag>
                    <span class="retrieval-score">{{ hit.score.toFixed(3) }}</span>
                  </div>
                  <span class="retrieval-title">{{ hit.title }}</span>
                </div>
                <div class="retrieval-content">{{ hit.answer || hit.content }}</div>
              </div>
              <a-empty v-if="retrievalRan && retrievalHits.length === 0" description="没有找到匹配内容" />
            </div>
          </div>
        </a-tab-pane>
      </a-tabs>
    </div>

    <!-- 上传弹窗 -->
    <a-modal v-model:open="uploadVisible" title="上传文档" :width="uploadDialogWidth" :mask-closable="false">
      <a-upload-dragger
        drag
        accept=".txt,.md,.pdf"
        :max-count="5"
        :before-upload="beforeUpload"
        :file-list="fileList"
        @change="onFileChange"
      >
        <p class="upload-icon"><InboxOutlined /></p>
        <div class="upload-text">拖拽文件到此处，或 <em>点击上传</em></div>
        <template #tip>
          <div class="upload-tip">支持 TXT / MD / PDF，单文件最大 10MB</div>
        </template>
      </a-upload-dragger>
      <template #footer>
        <a-button @click="uploadVisible = false">取消</a-button>
        <a-button type="primary" :loading="uploading" :disabled="fileList.length === 0" @click="doUpload">
          开始上传
        </a-button>
      </template>
    </a-modal>

    <!-- 分块预览弹窗 -->
    <a-modal v-model:open="chunksVisible" :title="`分块预览 — ${viewingDoc?.name}`" :width="chunksDialogWidth" :footer="null">
      <div v-if="chunksLoading" class="chunks-loading">
        <span class="rotating chunks-loading-icon"><LoadingOutlined /></span>
      </div>
      <div v-else class="chunks-list">
        <div v-for="chunk in chunks" :key="chunk.id" class="chunk-item">
          <div class="chunk-header">
            <span class="chunk-index">#{{ chunk.chunkIndex + 1 }}</span>
            <span class="chunk-length">约 {{ chunk.tokenCount }} 字</span>
          </div>
          <div class="chunk-content" :class="{ expanded: expandedChunks.has(chunk.id) }">
            {{ chunk.content }}
          </div>
          <a-button
            v-if="chunk.content.length > 200"
            type="link" size="small"
            @click="toggleChunk(chunk.id)"
          >
            {{ expandedChunks.has(chunk.id) ? '收起' : '展开全文' }}
          </a-button>
        </div>
        <a-empty v-if="chunks.length === 0" description="暂无分块" />
      </div>
    </a-modal>

    <a-modal v-model:open="faqDialogVisible" :title="editingFaqId ? '编辑 FAQ' : '新增 FAQ'" :width="faqDialogWidth">
      <a-form layout="vertical" class="faq-form">
        <a-form-item label="问题">
          <a-input v-model:value="faqForm.question" data-testid="faq-question-input" />
        </a-form-item>
        <a-form-item label="答案">
          <a-textarea v-model:value="faqForm.answer" data-testid="faq-answer-input" :rows="4" class="faq-answer-input" />
        </a-form-item>
        <a-form-item label="相似问法">
          <a-input v-model:value="faqForm.alternativeQuestionsText" placeholder="用 | 分隔多个问法" />
        </a-form-item>
        <a-form-item label="关键词">
          <a-input v-model:value="faqForm.keywordsText" data-testid="faq-keywords-input" placeholder="用 | 分隔多个关键词" />
        </a-form-item>
        <div class="faq-form-grid">
          <a-form-item label="分类">
            <a-input v-model:value="faqForm.category" />
          </a-form-item>
          <a-form-item label="优先级">
            <a-input-number v-model:value="faqForm.priority" :min="0" :max="1000" class="full-width-control" />
          </a-form-item>
        </div>
        <a-form-item label="状态">
          <a-switch v-model:checked="faqForm.enabled" checked-children="启用" un-checked-children="停用" />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="faqDialogVisible = false">取消</a-button>
        <a-button type="primary" data-testid="faq-save-button" :loading="faqSaving" @click="saveFaq">保存</a-button>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal, Upload } from 'ant-design-vue'
import type { UploadChangeParam, UploadFile } from 'ant-design-vue'
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  FileTextOutlined,
  InboxOutlined,
  LoadingOutlined,
  PlusOutlined,
  SearchOutlined,
  SettingOutlined,
  UploadOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import {
  listDocuments, getDocument, deleteDocument,
  getChunks, uploadDocument, getKb,
  listFaqs, createFaq, updateFaq, deleteFaq,
  importFaqCsv, exportFaqCsv, retrievalTest,
} from '@/api/knowledge'
import type { KnowledgeDocument, ChunkVO, KnowledgeFaq, RetrievalHit, RetrievalMode } from '@/api/knowledge'

const route = useRoute()
const router = useRouter()
const kbId = Number(route.params.kbId)
const uploadDialogWidth = '28.75rem'
const chunksDialogWidth = '42.5rem'
const faqDialogWidth = '36rem'

const kbName = ref('')
const activeTab = ref<'documents' | 'faqs' | 'retrieval'>('documents')
const docList = ref<KnowledgeDocument[]>([])
const uploadVisible = ref(false)
const uploading = ref(false)
const fileList = ref<UploadFile[]>([])
const faqCsvInputRef = ref<HTMLInputElement>()

// 分块预览
const chunksVisible = ref(false)
const chunksLoading = ref(false)
const chunks = ref<ChunkVO[]>([])
const viewingDoc = ref<KnowledgeDocument | null>(null)
const expandedChunks = ref(new Set<number>())

// 轮询
const pollingMap = ref(new Map<number, ReturnType<typeof setInterval>>())

const faqList = ref<KnowledgeFaq[]>([])
const faqDialogVisible = ref(false)
const faqSaving = ref(false)
const editingFaqId = ref<number | null>(null)
const faqForm = ref({
  question: '',
  answer: '',
  alternativeQuestionsText: '',
  keywordsText: '',
  category: '',
  priority: 0,
  enabled: true,
})
const retrievalQuery = ref('')
const retrievalTopK = ref(5)
const retrievalMode = ref<RetrievalMode>('auto')
const retrievalScoreThreshold = ref(0)
const retrievalRerank = ref(false)
const retrievalAdvancedOpen = ref(false)
const retrievalLoading = ref(false)
const retrievalRan = ref(false)
const retrievalHits = ref<RetrievalHit[]>([])
const retrievalModeOptions: Array<{ label: string; value: RetrievalMode }> = [
  { label: '智能推荐', value: 'auto' },
  { label: '综合匹配', value: 'hybrid' },
  { label: '语义理解', value: 'semantic' },
  { label: '关键词匹配', value: 'keyword' },
  { label: '仅问答库', value: 'faq' },
]
const knowledgeLifecycleSteps = ['导入内容', '解析分块', '生成索引', '维护 FAQ', '测试检索', '绑定应用']

onMounted(async () => {
  try {
    const kb = await getKb(kbId)
    kbName.value = kb.name
  } catch { /* ignore */ }
  await loadDocs()
})

onUnmounted(() => {
  pollingMap.value.forEach(t => clearInterval(t))
})

async function onTabChange(name: string | number) {
  if (name === 'faqs') await loadFaqs()
}

async function loadDocs() {
  try {
    const res = await listDocuments(kbId, { pageSize: 100 })
    docList.value = res.list
    // 对 PENDING/PROCESSING 状态的文档开启轮询
    for (const doc of res.list) {
      if (doc.status === 'PENDING' || doc.status === 'PROCESSING') {
        startPolling(doc.id)
      }
    }
  } catch { /* ignore */ }
}

async function loadFaqs() {
  try {
    const res = await listFaqs(kbId, { pageSize: 100 })
    faqList.value = res.list
  } catch { /* ignore */ }
}

function startPolling(docId: number) {
  if (pollingMap.value.has(docId)) return
  const timer = setInterval(async () => {
    try {
      const updated = await getDocument(docId)
      const idx = docList.value.findIndex(d => d.id === docId)
      if (idx >= 0) docList.value[idx] = updated
      if (updated.status === 'DONE' || updated.status === 'FAILED') {
        clearInterval(pollingMap.value.get(docId))
        pollingMap.value.delete(docId)
      }
    } catch { /* ignore */ }
  }, 3000)
  pollingMap.value.set(docId, timer)
}

// 上传
function beforeUpload(file: File) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['txt', 'md', 'pdf'].includes(ext ?? '')) {
    message.error('只支持 TXT / MD / PDF 格式')
    return Upload.LIST_IGNORE
  }
  if (file.size > 10 * 1024 * 1024) {
    message.error('文件大小不能超过 10MB')
    return Upload.LIST_IGNORE
  }
  return false
}

function onFileChange(info: UploadChangeParam<UploadFile>) {
  fileList.value = info.fileList.slice(0, 5)
}

async function doUpload() {
  if (fileList.value.length === 0) return
  uploading.value = true
  try {
    for (const f of fileList.value) {
      const raw = f.originFileObj as File | undefined
      if (!raw) continue
      const doc = await uploadDocument(kbId, raw)
      docList.value.unshift(doc)
      startPolling(doc.id)
    }
    fileList.value = []
    uploadVisible.value = false
    message.success('上传成功，正在后台处理中…')
  } catch (e: unknown) {
    message.error((e as Error).message || '上传失败')
  } finally {
    uploading.value = false
  }
}

// 分块预览
async function viewChunks(doc: KnowledgeDocument) {
  viewingDoc.value = doc
  chunksVisible.value = true
  chunksLoading.value = true
  expandedChunks.value = new Set()
  try {
    chunks.value = await getChunks(doc.id)
  } finally {
    chunksLoading.value = false
  }
}

function toggleChunk(id: number) {
  if (expandedChunks.value.has(id)) expandedChunks.value.delete(id)
  else expandedChunks.value.add(id)
}

// 删除
async function onDelete(doc: KnowledgeDocument) {
  Modal.confirm({
    title: '提示',
    content: `确定删除文档「${doc.name}」？`,
    okText: '确认',
    cancelText: '取消',
    onOk: async () => {
      await deleteDocument(doc.id)
      docList.value = docList.value.filter(d => d.id !== doc.id)
      clearInterval(pollingMap.value.get(doc.id))
      pollingMap.value.delete(doc.id)
      message.success('删除成功')
    },
  })
}

function openCreateFaq() {
  editingFaqId.value = null
  faqForm.value = {
    question: '',
    answer: '',
    alternativeQuestionsText: '',
    keywordsText: '',
    category: '',
    priority: 0,
    enabled: true,
  }
  faqDialogVisible.value = true
}

function openEditFaq(faq: KnowledgeFaq) {
  editingFaqId.value = faq.id
  faqForm.value = {
    question: faq.question,
    answer: faq.answer,
    alternativeQuestionsText: faq.alternativeQuestions.join('|'),
    keywordsText: faq.keywords.join('|'),
    category: faq.category,
    priority: faq.priority,
    enabled: faq.enabled,
  }
  faqDialogVisible.value = true
}

async function saveFaq() {
  const payload = {
    question: faqForm.value.question.trim(),
    answer: faqForm.value.answer.trim(),
    alternativeQuestions: splitFormList(faqForm.value.alternativeQuestionsText),
    keywords: splitFormList(faqForm.value.keywordsText),
    category: faqForm.value.category.trim(),
    priority: faqForm.value.priority,
    enabled: faqForm.value.enabled,
  }
  if (!payload.question || !payload.answer) {
    message.error('问题和答案不能为空')
    return
  }
  faqSaving.value = true
  try {
    if (editingFaqId.value) {
      await updateFaq(editingFaqId.value, payload)
      message.success('FAQ 已更新')
    } else {
      await createFaq(kbId, payload)
      message.success('FAQ 已创建')
    }
    faqDialogVisible.value = false
    await loadFaqs()
  } finally {
    faqSaving.value = false
  }
}

async function onDeleteFaq(faq: KnowledgeFaq) {
  Modal.confirm({
    title: '提示',
    content: `确定删除 FAQ「${faq.question}」？`,
    okText: '确认',
    cancelText: '取消',
    onOk: async () => {
      await deleteFaq(faq.id)
      faqList.value = faqList.value.filter(item => item.id !== faq.id)
      message.success('删除成功')
    },
  })
}

function openFaqImport() {
  faqCsvInputRef.value?.click()
}

async function onFaqCsvSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    const result = await importFaqCsv(kbId, file)
    message.success(`已导入 ${result.imported} 条 FAQ`)
    await loadFaqs()
  } catch (e: unknown) {
    message.error((e as Error).message || '导入失败')
  }
}

async function downloadFaqCsv() {
  try {
    const text = await exportFaqCsv(kbId)
    const blob = new Blob([text], { type: 'text/csv;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${kbName.value || 'knowledge'}-faq.csv`
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (e: unknown) {
    message.error((e as Error).message || '导出失败')
  }
}

async function runRetrievalTest() {
  if (!retrievalQuery.value.trim()) {
    message.error('请输入测试问题')
    return
  }
  retrievalLoading.value = true
  retrievalRan.value = true
  try {
    const result = await retrievalTest(kbId, {
      query: retrievalQuery.value.trim(),
      topK: retrievalTopK.value,
      retrievalMode: retrievalMode.value,
      scoreThreshold: retrievalScoreThreshold.value,
      rerank: retrievalRerank.value,
    })
    retrievalHits.value = result.hits
  } finally {
    retrievalLoading.value = false
  }
}

function splitFormList(value: string) {
  return value.split('|').map(item => item.trim()).filter(Boolean)
}

function sourceLabel(sourceType: string) {
  return sourceType === 'FAQ' ? 'FAQ' : '文档分块'
}

function matchTypeLabel(matchType: string) {
  const labels: Record<string, string> = {
    EXACT: '精准命中',
    KEYWORD: '关键词',
    VECTOR: '语义',
    HYBRID: '综合',
  }
  return labels[matchType] ?? matchType
}

// 工具函数
const STATUS_MAP = {
  PENDING:    { label: '待处理', type: 'default' },
  PROCESSING: { label: '处理中', type: 'processing' },
  DONE:       { label: '已完成', type: 'success' },
  FAILED:     { label: '失败',   type: 'error' },
} as const

function statusLabel(s: string) { return STATUS_MAP[s as keyof typeof STATUS_MAP]?.label ?? s }
function statusType(s: string) { return STATUS_MAP[s as keyof typeof STATUS_MAP]?.type ?? 'default' }

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function formatTime(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth()+1}/${d.getDate()} ${d.toTimeString().slice(0,5)}`
}
</script>

<style scoped>
.page-header { margin-bottom: var(--space-4); }
.back-button {
  margin-right: var(--space-2);
  padding: 0;
}

.hify-card {
  background: var(--color-bg-card, #fff);
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.knowledge-lifecycle {
  align-items: center;
  background: var(--color-bg-subtle, #f8fafc);
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
  border-radius: var(--radius-lg);
  display: grid;
  gap: var(--space-2);
  grid-template-columns: repeat(6, minmax(0, 1fr));
  margin-bottom: var(--space-4);
  padding: var(--space-3);
}

.knowledge-lifecycle-step {
  align-items: center;
  color: var(--color-text-secondary, #4b5563);
  display: flex;
  font-size: var(--text-xs);
  gap: var(--space-2);
  min-width: 0;
}

.knowledge-lifecycle-index {
  align-items: center;
  background: var(--color-primary-50, #eef2ff);
  border-radius: 999rem;
  color: var(--color-primary-600, #4f46e5);
  display: inline-flex;
  flex: 0 0 1.25rem;
  font-size: var(--text-xs);
  font-weight: 700;
  height: 1.25rem;
  justify-content: center;
  width: 1.25rem;
}

.kb-tabs {
  padding: 0 var(--space-4) var(--space-4);
}

.kb-tabs :deep(.ant-tabs-nav) {
  margin-bottom: var(--space-3);
}

.kb-tabs :deep(.ant-tabs-tab) {
  color: var(--color-text-primary, #0f1117);
  font-weight: 600;
  padding: 0 var(--space-4);
}

.kb-tabs :deep(.ant-tabs-tab-active .ant-tabs-tab-btn) {
  color: var(--color-primary-600, #4f46e5);
}

.kb-tabs :deep(.ant-tabs-tab-btn:focus-visible) {
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-focus-ring);
}

.hidden-input {
  display: none;
}

.knowledge-table-shell {
  overflow-x: auto;
  padding-bottom: var(--space-1);
}

.knowledge-table {
  color: var(--color-text-secondary, #4b5563);
  display: grid;
  font-size: var(--text-sm);
  min-width: 62rem;
}

.document-table .knowledge-table-row {
  grid-template-columns: minmax(14rem, 1.5fr) 5rem 6rem 5.5rem 7.5rem 8.5rem 9rem;
}

.faq-table .knowledge-table-row {
  grid-template-columns: minmax(16rem, 1.2fr) minmax(18rem, 1fr) 11rem 7rem 5rem 6rem 8rem;
}

.knowledge-table-row {
  align-items: center;
  border-bottom: 0.0625rem solid var(--color-border-default, #e3e6ef);
  display: grid;
  gap: var(--space-3);
  min-height: 3.5rem;
  padding: var(--space-3) var(--space-3);
}

.knowledge-table-row > div {
  min-width: 0;
}

.knowledge-table-head {
  background: var(--color-bg-page, #f8f9fc);
  color: var(--color-text-secondary, #4b5563);
  font-weight: 700;
  min-height: 2.75rem;
}

.knowledge-table:not(:has(.knowledge-table-row:nth-child(2))) .knowledge-table-head {
  border-bottom: none;
}

.table-actions {
  align-items: center;
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
  white-space: nowrap;
}

.table-actions :deep(.ant-btn + .ant-btn) {
  margin-left: 0;
}

.doc-name {
  display: flex;
  align-items: center;
  gap: 0.4375rem;
  font-size: 0.84375rem;
  font-weight: 500;
  min-width: 0;
}

.doc-name span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.button-icon,
.doc-icon,
.inline-icon,
.error-icon,
.chunks-loading-icon,
.upload-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.doc-icon { color: var(--color-primary-400, #818cf8); flex-shrink: 0; }

.status-cell { display: flex; align-items: center; gap: 0.375rem; }
.error-icon { color: var(--color-danger-500, #ef4444); cursor: pointer; }

.chunk-count { font-weight: 600; color: var(--color-primary-500, #6366f1); }
.text-muted { color: var(--color-text-tertiary, #8b92a8); }

.table-empty { padding: var(--space-10) 0; }

.faq-question {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary, #0f1117);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.faq-subline {
  margin-top: 0.25rem;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary, #8b92a8);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.faq-answer {
  color: var(--color-text-secondary, #4b5563);
  display: -webkit-box;
  font-size: var(--text-sm);
  line-height: 1.45;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.faq-form-grid {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: minmax(0, 1fr) 8.75rem;
}

.retrieval-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.retrieval-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.retrieval-toolbar {
  align-items: center;
  display: grid;
  gap: var(--space-3);
  grid-template-columns: minmax(18rem, 1fr) 12rem 9rem 7.5rem 8.5rem;
}

.retrieval-query-input,
.retrieval-mode-select,
.retrieval-topk-input,
.retrieval-advanced-button,
.retrieval-search-button {
  min-width: 0;
  width: 100%;
}

.retrieval-topk-input {
  flex: none;
}

.retrieval-advanced-button,
.retrieval-search-button {
  justify-content: center;
  white-space: nowrap;
}

.retrieval-advanced {
  align-items: center;
  background: var(--color-bg-subtle, #f8fafc);
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
  border-radius: var(--radius-md);
  display: grid;
  gap: var(--space-3);
  grid-template-columns: 12rem 14rem;
  padding: var(--space-3);
}

.retrieval-advanced :deep(.ant-form-item) {
  margin-bottom: 0;
}

.retrieval-results {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.retrieval-hit {
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}

.retrieval-hit-header {
  align-items: center;
  display: flex;
  gap: var(--space-3);
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.retrieval-score {
  color: var(--color-text-tertiary, #8b92a8);
  font-size: var(--text-xs);
  margin-left: 0.375rem;
}

.retrieval-title {
  color: var(--color-text-secondary, #4b5563);
  font-size: var(--text-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.retrieval-content {
  color: var(--color-text-primary, #0f1117);
  font-size: var(--text-sm);
  line-height: 1.65;
  white-space: pre-wrap;
}

@media (max-width: 56rem) {
  .knowledge-lifecycle,
  .retrieval-toolbar,
  .retrieval-advanced {
    grid-template-columns: 1fr;
  }
}

.upload-tip {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary, #8b92a8);
  margin-top: 0.375rem;
  text-align: center;
}
.upload-icon {
  font-size: 3rem;
}
.upload-text {
  font-size: var(--text-sm);
  color: var(--color-text-primary, #0f1117);
}
.chunks-loading {
  text-align: center;
  padding: 1.875rem;
}
.chunks-loading-icon {
  font-size: 1.75rem;
}

/* 分块列表 */
.chunks-list {
  max-height: 60vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.chunk-item {
  border: 0.0625rem solid var(--color-border-default, #e3e6ef);
  border-radius: var(--radius-lg);
  padding: var(--space-3) 0.875rem;
}
.chunk-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}
.chunk-index {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-primary-500, #6366f1);
  background: var(--color-primary-50, #eef2ff);
  padding: 0.125rem var(--space-2);
  border-radius: var(--radius-sm);
}
.chunk-length {
  font-size: 0.6875rem;
  color: var(--color-text-tertiary, #8b92a8);
}
.chunk-content {
  font-size: var(--text-sm);
  line-height: 1.65;
  color: var(--color-text-primary, #0f1117);
  max-height: 3.75rem;
  overflow: hidden;
  transition: max-height 0.3s;
}
.chunk-content.expanded { max-height: none; }

/* 旋转动画 */
.rotating {
  animation: spin 1s linear infinite;
}
.full-width-control {
  width: 100%;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
</style>
