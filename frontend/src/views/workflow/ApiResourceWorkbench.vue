<template>
  <main class="api-resource-page">
    <header class="api-resource-header">
      <div>
        <h1>API Resource</h1>
        <p>配置 HTTP 接口，测试后包装成工作流可调用的业务工具。</p>
      </div>
      <a-button @click="router.push({ name: 'HifyWorkflows' })">返回工作流</a-button>
    </header>

    <section class="api-resource-grid">
      <form class="api-resource-panel" data-testid="api-resource-form" @submit.prevent="submitResource">
        <div class="panel-title">
          <strong>技术资源</strong>
          <span>HTTP endpoint</span>
        </div>
        <a-input v-model:value="resourceForm.name" data-testid="api-resource-name" placeholder="资源名称" />
        <div class="method-row">
          <a-select :virtual="false" v-model:value="resourceForm.method" data-testid="api-resource-method" aria-label="请求方法">
            <a-select-option value="GET">GET</a-select-option>
            <a-select-option value="POST">POST</a-select-option>
            <a-select-option value="PUT">PUT</a-select-option>
            <a-select-option value="DELETE">DELETE</a-select-option>
          </a-select>
          <a-input v-model:value="resourceForm.endpoint" data-testid="api-resource-endpoint" placeholder="https://api.example.com/orders/{{orderId}}" />
        </div>
        <a-input v-model:value="resourceForm.description" placeholder="说明" />
        <a-textarea v-model:value="headersText" :rows="3" data-testid="api-resource-headers" placeholder='[{"name":"X-Token","value":"secret","sensitive":true}]' />
        <a-textarea v-model:value="inputSchemaText" :rows="5" data-testid="api-resource-input-schema" placeholder='{"type":"object","properties":{"orderId":{"type":"string"}},"required":["orderId"]}' />
        <a-textarea v-model:value="testPayloadText" :rows="3" data-testid="api-resource-test-payload" placeholder='{"orderId":"A-100"}' />
        <div class="panel-actions">
          <a-button html-type="submit" type="primary" :loading="savingResource" data-testid="api-resource-create">创建资源</a-button>
          <a-button :disabled="!selectedResource" :loading="testingResource" data-testid="api-resource-test" @click="testSelectedResource">测试调用</a-button>
        </div>
        <pre v-if="testResult" class="result-box" data-testid="api-resource-test-result">{{ JSON.stringify(testResult, null, 2) }}</pre>
      </form>

      <form class="api-resource-panel" data-testid="api-tool-form" @submit.prevent="submitTool">
        <div class="panel-title">
          <strong>业务工具</strong>
          <span>Tool Builder Lite</span>
        </div>
        <a-select :virtual="false" v-model:value="toolForm.apiResourceId" data-testid="api-tool-resource" placeholder="选择 API Resource">
          <a-select-option
            v-for="resource in resources"
            :key="resource.id"
            :value="resource.id"
          >
            {{ resource.name }}
          </a-select-option>
        </a-select>
        <a-input v-model:value="toolForm.name" data-testid="api-tool-name" placeholder="工具名称，例如 lookup_order_api" />
        <a-input v-model:value="toolForm.displayName" placeholder="显示名" />
        <a-input v-model:value="toolForm.description" placeholder="说明" />
        <label class="model-callable-row">
          <span>模型可调用</span>
          <a-switch v-model:checked="toolForm.modelCallable" data-testid="api-tool-model-callable" />
        </label>
        <div class="panel-actions">
          <a-button html-type="submit" type="primary" :disabled="!toolForm.apiResourceId" :loading="savingTool" data-testid="api-tool-create">创建 Tool</a-button>
        </div>
        <div class="tool-list" data-testid="api-tool-list">
          <button
            v-for="tool in tools"
            :key="tool.resourceId"
            type="button"
            class="tool-row"
          >
            <span>
              <strong>{{ tool.displayName || tool.name }}</strong>
              <small>{{ tool.resourceId }}</small>
            </span>
            <em>{{ tool.modelCallable ? 'model' : 'workflow' }}</em>
          </button>
        </div>
      </form>
    </section>

    <section class="api-resource-panel resource-list" data-testid="api-resource-list">
      <div class="panel-title">
        <strong>资源列表</strong>
        <span>{{ resources.length }} 个资源</span>
      </div>
      <button
        v-for="resource in resources"
        :key="resource.id"
        type="button"
        class="resource-row"
        :class="{ active: selectedResource?.id === resource.id }"
        @click="selectResource(resource)"
      >
        <span>
          <strong>{{ resource.name }}</strong>
          <small>{{ resource.method }} {{ resource.endpoint }}</small>
        </span>
        <em>{{ resource.enabled ? '启用' : '停用' }}</em>
      </button>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'

import {
  createApiResource,
  createApiTool,
  listApiResources,
  listApiTools,
  testApiResourceCall,
} from '@/api/workflow'

const router = useRouter()
const resources = ref<any[]>([])
const tools = ref<any[]>([])
const selectedResourceId = ref<number>(0)
const savingResource = ref(false)
const testingResource = ref(false)
const savingTool = ref(false)
const testResult = ref<Record<string, any> | null>(null)

const resourceForm = reactive({
  name: '',
  description: '',
  method: 'GET',
  endpoint: '',
})
const headersText = ref('[]')
const inputSchemaText = ref('{"type":"object","properties":{},"required":[]}')
const testPayloadText = ref('{}')

const toolForm = reactive({
  name: '',
  displayName: '',
  description: '',
  apiResourceId: 0,
  modelCallable: true,
})

const selectedResource = computed(() => resources.value.find((resource) => Number(resource.id) === selectedResourceId.value) || null)

function parseJsonObject(text: string, fallback: Record<string, any> = {}) {
  try {
    const parsed = JSON.parse(text || '{}')
    return parsed && typeof parsed === 'object' ? parsed : fallback
  } catch {
    return fallback
  }
}

function parseJsonList(text: string) {
  const parsed = parseJsonObject(text, {})
  if (Array.isArray(parsed)) return parsed
  return Object.keys(parsed).length ? parsed : []
}

async function loadData() {
  const [resourceResult, toolResult] = await Promise.all([
    listApiResources({ pageSize: 100 }),
    listApiTools({ pageSize: 100, adapterType: 'API_RESOURCE' }),
  ])
  resources.value = Array.isArray(resourceResult.list) ? resourceResult.list : []
  tools.value = Array.isArray(toolResult.list) ? toolResult.list : []
  if (!selectedResourceId.value && resources.value[0]) selectResource(resources.value[0])
}

function selectResource(resource: any) {
  selectedResourceId.value = Number(resource.id)
  toolForm.apiResourceId = Number(resource.id)
  if (!toolForm.name) {
    toolForm.name = `${String(resource.name || 'api').trim().toLowerCase().replace(/[^a-z0-9]+/g, '_')}_tool`
    toolForm.displayName = `${resource.name} Tool`
  }
}

async function submitResource() {
  savingResource.value = true
  try {
    const resource = await createApiResource({
      ...resourceForm,
      authMode: 'none',
      headers: parseJsonList(headersText.value),
      inputSchema: parseJsonObject(inputSchemaText.value, { type: 'object', properties: {}, required: [] }),
      outputSchema: { type: 'object', properties: { body: { type: 'string' } } },
      testPayload: parseJsonObject(testPayloadText.value),
      timeoutMs: 30000,
      enabled: true,
    })
    message.success('API Resource 已创建')
    await loadData()
    const created = resources.value.find((item) => Number(item.id) === Number(resource.id))
    if (created) selectResource(created)
  } finally {
    savingResource.value = false
  }
}

async function testSelectedResource() {
  if (!selectedResource.value) return
  testingResource.value = true
  try {
    testResult.value = await testApiResourceCall(Number(selectedResource.value.id), parseJsonObject(testPayloadText.value))
  } finally {
    testingResource.value = false
  }
}

async function submitTool() {
  savingTool.value = true
  try {
    await createApiTool({
      name: toolForm.name,
      displayName: toolForm.displayName || toolForm.name,
      description: toolForm.description,
      adapterType: 'API_RESOURCE',
      apiResourceId: Number(toolForm.apiResourceId),
      inputSchema: parseJsonObject(inputSchemaText.value, { type: 'object', properties: {}, required: [] }),
      outputSchema: { type: 'object', properties: { result: { type: 'string' } } },
      modelCallable: toolForm.modelCallable,
      enabled: true,
      timeoutMs: 30000,
      retryCount: 0,
      errorBehavior: 'fail',
    })
    message.success('Tool 已创建')
    await loadData()
  } finally {
    savingTool.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.api-resource-page {
  min-height: 100vh;
  padding: 1.5rem;
  background: #f6f8fb;
  color: #1f2937;
}

.api-resource-header,
.api-resource-grid {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1rem;
  align-items: start;
  max-width: 73.75rem;
  margin: 0 auto 1rem;
}

.api-resource-header h1 {
  margin: 0 0 0.375rem;
  font-size: 1.75rem;
  line-height: 1.2;
}

.api-resource-header p {
  margin: 0;
  color: #64748b;
}

.api-resource-grid {
  grid-template-columns: minmax(0, 1fr) minmax(20rem, 26.25rem);
}

.api-resource-panel {
  display: grid;
  gap: 0.75rem;
  padding: 1rem;
  border: 0.0625rem solid #d9e1ef;
  border-radius: 0.5rem;
  background: #fff;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.panel-title strong {
  font-size: 1rem;
}

.panel-title span,
.tool-row small,
.resource-row small {
  color: #64748b;
}

.method-row {
  display: grid;
  grid-template-columns: 7.5rem minmax(0, 1fr);
  gap: 0.5rem;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.result-box {
  max-height: 15rem;
  overflow: auto;
  padding: 0.75rem;
  border: 0.0625rem solid #d9e1ef;
  border-radius: 0.375rem;
  background: #f8fafc;
  white-space: pre-wrap;
}

.model-callable-row,
.tool-row,
.resource-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.tool-list {
  display: grid;
  gap: 0.5rem;
  max-height: 20rem;
  overflow: auto;
}

.tool-row,
.resource-row {
  width: 100%;
  padding: 0.625rem 0.75rem;
  border: 0.0625rem solid #d9e1ef;
  border-radius: 0.375rem;
  background: #fff;
  text-align: left;
}

.tool-row span,
.resource-row span {
  display: grid;
  gap: 0.25rem;
  min-width: 0;
}

.tool-row small,
.resource-row small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-list {
  max-width: 73.75rem;
  margin: 0 auto;
}

.resource-row.active {
  border-color: #6366f1;
  background: #eef2ff;
}

.api-resource-page :deep(textarea) {
  resize: none;
}

@media (max-width: 56.25rem) {
  .api-resource-header,
  .api-resource-grid {
    grid-template-columns: 1fr;
  }
}
</style>
