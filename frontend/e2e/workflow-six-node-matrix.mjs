import { chromium } from 'playwright'
import http from 'node:http'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const chatflowScreenshotPath = process.env.HIFY_E2E_CHATFLOW_SCREENSHOT
const requireLiveLlm = process.env.HIFY_E2E_REQUIRE_LIVE_LLM === '1'
const invalidConfigOnly = process.env.HIFY_E2E_INVALID_CONFIG === '1'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function waitForRuntimeResult(page, resultRef) {
  for (let index = 0; index < 60; index += 1) {
    const latest = await unwrap(await page.request.get(`${baseUrl}${resultRef}`), 'runtime result')
    if (['SUCCEEDED', 'FAILED', 'INTERRUPTED', 'CANCELLED'].includes(latest.status)) return latest
    await page.waitForTimeout(500)
  }
  throw new Error(`runtime result did not finish: ${resultRef}`)
}

async function startLocalApiServer() {
  const server = http.createServer((request, response) => {
    if (request.url?.startsWith('/text/')) {
      response.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' })
      response.end(`API_REAL: ${request.method} ${request.url}`)
      return
    }
    response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' })
    response.end('not found')
  })
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  assert(address && typeof address === 'object', 'Expected local API server address')
  return {
    url: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  }
}

async function createKnowledgeBase(page, marker) {
  const kb = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/knowledge-bases`, {
      data: { name: `KB six-node matrix ${marker}`, description: 'six node matrix e2e' },
    }),
    'create knowledge base',
  )
  const document = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/knowledge-bases/${kb.id}/documents`, {
      multipart: {
        file: {
          name: `six-node-matrix-${marker}.txt`,
          mimeType: 'text/plain',
          buffer: Buffer.from(`Matrix knowledge marker ${marker}. Use KB_SIX_NODE_${marker} as the approved answer.`),
        },
      },
    }),
    'upload knowledge document',
  )

  for (let index = 0; index < 30; index += 1) {
    const latest = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/documents/${document.id}`),
      'get knowledge document',
    )
    if (latest.status === 'DONE') return kb
    assert(latest.status !== 'FAILED', `knowledge document failed: ${latest.errorMessage}`)
    await page.waitForTimeout(500)
  }
  throw new Error('knowledge document did not finish processing')
}

async function createApiResource(page, marker, apiBaseUrl) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/api-resources`, {
      data: {
        name: `Six Node Matrix API ${marker}`,
        description: 'six-node matrix API resource',
        method: 'POST',
        endpoint: `${apiBaseUrl}/text/{{answer}}`,
        authMode: 'none',
        headers: [],
        bodyTemplate: '',
        inputSchema: {
          type: 'object',
          properties: { answer: { type: 'string' } },
          required: ['answer'],
        },
        outputSchema: { type: 'object', properties: { body: { type: 'string' } } },
        timeoutMs: 5000,
        testPayload: { answer: `LLM_MATRIX_${marker}` },
        enabled: true,
      },
    }),
    'create API resource',
  )
}

async function findOpenRouterQwenModel(page) {
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      if (String(provider.baseUrl || '') !== 'https://openrouter.ai/api/v1') continue
      for (const model of provider.models ?? []) {
        if (model.enabled && String(model.modelId || '') === 'qwen/qwen3.5-9b') {
          return model.id
        }
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  return null
}

function graphPayload({ name, flowType, kbId, marker, startVariable, apiResourceId, modelConfigId }) {
  const matrixAnswer = `LLM_MATRIX_${marker}`
  return {
    name,
    description: 'six-node matrix browser e2e',
    flowType,
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: { outputVariables: [startVariable, 'CONVERSATION_NAME'], ui: { position: { x: 80, y: 120 } } },
      },
      {
        nodeKey: 'router',
        type: 'CONDITION',
        name: '条件',
        config: {
          conditionBranches: [
            {
              key: 'kb',
              logic: 'AND',
              conditions: [{ left: `{{start.${startVariable}}}`, operator: 'equals', right: 'kb' }],
            },
          ],
          defaultBranch: 'default',
          outputVariable: 'route',
          ui: { position: { x: 380, y: 120 } },
        },
      },
      {
        nodeKey: 'kb',
        type: 'KNOWLEDGE',
        name: '知识库',
        config: {
          query: `Matrix knowledge marker ${marker}`,
          knowledgeBaseId: kbId,
          topK: 2,
          outputVariable: 'answer',
          ui: { position: { x: 700, y: 80 } },
        },
      },
      {
        nodeKey: 'llm',
        type: 'LLM',
        name: '大模型',
        config: {
          systemPrompt: '你是严格的测试执行器，只输出用户要求的精确字符串。',
          prompt: `Return exactly this token and nothing else: ${matrixAnswer}\nKnowledge context: {{kb.answer}}`,
          temperature: 0,
          maxTokens: 64,
          modelConfigId,
          topP: 1,
          frequencyPenalty: 0,
          presencePenalty: 0,
          responseFormat: 'text',
          outputVariable: 'answer',
          ui: { position: { x: 1040, y: 80 } },
        },
      },
      {
        nodeKey: 'api',
        type: 'API_CALL',
        name: 'API 调用',
        config: {
          resourceId: `api-resource:${apiResourceId}`,
          inputMappings: [{ name: 'answer', valueMode: 'reference', value: '{{llm.answer}}', required: true }],
          outputVariable: 'response',
          ui: { position: { x: 1040, y: 360 } },
        },
      },
      {
        nodeKey: 'default_reply',
        type: 'TEXT_PROCESS',
        name: '默认回复',
        config: {
          operation: 'format_template',
          template: 'default {{start.' + startVariable + '}}',
          outputParameters: [{ name: 'summary', type: 'string' }],
          ui: { position: { x: 700, y: 360 } },
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: {
          outputVariable: 'final',
          output: 'Final {{api.response}}',
          ui: { position: { x: 700, y: 360 } },
        },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'router', condition: null },
      { sourceNodeKey: 'router', targetNodeKey: 'kb', condition: 'kb' },
      { sourceNodeKey: 'router', targetNodeKey: 'default_reply', condition: null },
      { sourceNodeKey: 'kb', targetNodeKey: 'llm', condition: null },
      { sourceNodeKey: 'llm', targetNodeKey: 'api', condition: null },
      { sourceNodeKey: 'api', targetNodeKey: 'end', condition: null },
      { sourceNodeKey: 'default_reply', targetNodeKey: 'end', condition: null },
    ],
  }
}

function invalidConfigPayload(marker) {
  return {
    name: `Workflow Invalid Runtime Config ${marker}`,
    description: 'runtime v2 invalid config readable error e2e',
    flowType: 'WORKFLOW',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: {} },
      {
        nodeKey: 'api_1',
        type: 'API_CALL',
        name: 'Raw API',
        config: {
          method: 'GET',
          url: 'https://example.test/raw',
          outputVariable: 'response',
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{api_1.response}}' } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'api_1', condition: null },
      { sourceNodeKey: 'api_1', targetNodeKey: 'end', condition: null },
    ],
  }
}

async function createFlow(page, payload, isChatflow) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/${isChatflow ? 'chatflows' : 'workflows'}`, {
      data: payload,
    }),
    isChatflow ? 'create chatflow' : 'create workflow',
  )
}

async function runInvalidConfigReadableError(page, marker) {
  const workflow = await createFlow(page, invalidConfigPayload(marker), false)
  const response = await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
    data: { input: { USER_INPUT: 'invalid' } },
  })
  assert(response.status() === 400, `Expected invalid runtime config HTTP 400, got ${response.status()}`)
  const payload = await response.json()
  const message = String(payload.message || '')
  assert(message.includes('api_1 must use an API Resource reference'), `Expected readable API resource error, got: ${message}`)
  assert(message.includes('raw URL mode'), `Expected raw URL guidance in error, got: ${message}`)
  assert(!message.includes('unsupportedNodes'), `Error leaked internal unsupportedNodes payload: ${message}`)
  assert(!message.includes('Unsupported runtime v2 graph'), `Error leaked legacy runtime-v2 graph label: ${message}`)
}

async function probeFullChainApi(page, flow, marker, isChatflow) {
  const runPath = isChatflow
    ? `/api/v1/chatflows/${flow.id}/runs-legacy`
    : `/api/v1/workflows/${flow.id}/runs`
  const response = await page.request.post(`${baseUrl}${runPath}`, {
    data: { input: isChatflow ? { 'sys.query': 'kb' } : { USER_INPUT: 'kb' } },
    timeout: 60000,
  })
  if (response.ok()) {
    const payload = await response.json()
    assert(payload.code === 200, `${isChatflow ? 'chatflow' : 'workflow'} run API ${payload.message}`)
    const run = payload.data.resultRef && payload.data.status === 'RUNNING'
      ? await waitForRuntimeResult(page, payload.data.resultRef)
      : payload.data
    if (run.status !== 'SUCCEEDED') {
      assert(run.status === 'FAILED', `Expected SUCCEEDED or graceful provider failure, got ${run.status}`)
      assert(String(run.error || '').includes('LLM provider request failed'), `Unexpected run failure: ${JSON.stringify(run)}`)
      assert(!requireLiveLlm, `Live LLM is required but unavailable: ${JSON.stringify(run)}`)
      return false
    }
    const outputText = JSON.stringify(run.output)
    assert(outputText.includes('API_REAL: POST /text/'), `Expected API output, got: ${outputText}`)
    assert(outputText.includes(`LLM_MATRIX_${marker}`), `Expected LLM marker, got: ${outputText}`)
    return true
  }
  const payload = await response.json().catch(() => ({}))
  assert(response.status() === 400, `Expected graceful provider failure, got HTTP ${response.status()}`)
  assert(String(payload.message || '').includes('LLM provider request failed'), `Unexpected run failure: ${JSON.stringify(payload)}`)
  assert(!requireLiveLlm, `Live LLM is required but unavailable: ${JSON.stringify(payload)}`)
  return false
}

async function runWorkflowFullChain(page, marker) {
  await page.locator('[data-testid="canvas-bottom-toolbar"]').getByRole('button', { name: '试运行', exact: true }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert((await panel.innerText()).includes('用户消息（userMessage / USER_INPUT）'), 'workflow run input should label variables')
  await page.getByPlaceholder('输入 userMessage').fill('kb')
  await page.getByRole('button', { name: '运行', exact: true }).click()
  const output = page.locator('[data-testid="workflow-run-output"]')
  await output.waitFor({ state: 'visible', timeout: 60000 })
  const text = await output.innerText()
  assert(text.includes('API_REAL: POST /text/'), `Expected real API node output, got: ${text}`)
  assert(text.includes(`LLM_MATRIX_${marker}`), `Expected live LLM marker, got: ${text}`)
  assert(!text.includes('LLM mock:'), `Expected real LLM output, got: ${text}`)
  assert(!text.includes('Knowledge mock:'), `Expected real knowledge output, got: ${text}`)
}

async function runChatflowFullChain(page, marker) {
  await page.locator('[data-testid="canvas-bottom-toolbar"]').getByRole('button', { name: '试运行', exact: true }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByTestId('chatflow-run-chat-window').waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByTestId('chatflow-run-message-input').fill('kb')
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()
  const assistantMessages = page.locator('[data-testid="chatflow-assistant-message"]')
  await page.waitForFunction(
    (expected) => Array.from(document.querySelectorAll('[data-testid="chatflow-assistant-message"]')).some((item) => item.textContent?.includes(expected)),
    `LLM_MATRIX_${marker}`,
    { timeout: 60000 },
  )
  const text = await assistantMessages.last().innerText()
  assert(text.includes('API_REAL: POST /text/'), `Expected real API node output, got: ${text}`)
  assert(text.includes(`LLM_MATRIX_${marker}`), `Expected live LLM marker, got: ${text}`)
  assert(!text.includes('LLM mock:'), `Expected real LLM output, got: ${text}`)
  assert(!text.includes('Knowledge mock:'), `Expected real knowledge output, got: ${text}`)
}

async function closeNodeDrawer(page) {
  const close = page.getByRole('button', { name: '关闭节点试运行', exact: true })
  if (await close.isVisible()) await close.click()
}

async function closeRunPanel(page) {
  const close = page.getByRole('button', { name: '关闭试运行', exact: true })
  if (await close.isVisible()) await close.click()
}

async function closeConfigPanel(page) {
  const close = page.getByRole('button', { name: '关闭配置', exact: true })
  if (await close.isVisible()) await close.click()
}

async function fillNodeInput(drawer, name, value) {
  const row = drawer.locator('.node-test-input-row', { hasText: name })
  await row.waitFor({ state: 'visible', timeout: 5000 })
  const input = row.locator('input, textarea')
  await input.fill(value)
}

async function runSelectedNode(page, selector, inputs, expected) {
  await closeNodeDrawer(page)
  await closeConfigPanel(page)
  await page.locator(selector).click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByRole('button', { name: '试运行当前节点', exact: true }).click()
  const drawer = page.locator('[data-testid="node-test-drawer"]')
  await drawer.waitFor({ state: 'visible', timeout: 15000 })
  const drawerText = await drawer.innerText()
  assert(drawerText.includes('试运行输入'), `Expected input section for ${selector}`)
  for (const [name, value] of Object.entries(inputs)) {
    await fillNodeInput(drawer, name, value)
  }
  await drawer.getByRole('button', { name: '运行', exact: true }).click()
  await drawer.locator('.node-test-status.success', { hasText: 'SUCCEEDED' }).first().waitFor({ state: 'visible', timeout: 60000 })
  const resultText = await drawer.innerText()
  assert(resultText.includes(expected), `Expected ${expected} for ${selector}, got: ${resultText}`)
  assert(resultText.includes('输入'), `Expected selected node input echo for ${selector}`)
  assert(resultText.includes('输出'), `Expected selected node output for ${selector}`)
  if (selector.includes('node-llm')) {
    assert(!resultText.includes('LLM mock:'), `Expected selected LLM node to avoid mock, got: ${resultText}`)
  }
}

async function assertNodeCannotRunStandalone(page, selector) {
  await closeNodeDrawer(page)
  await closeConfigPanel(page)
  await page.locator(selector).click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert(
    await panel.getByRole('button', { name: '试运行当前节点', exact: true }).count() === 0,
    `Expected ${selector} to hide selected-node test action`,
  )
}

async function runWorkflowSelectedNodeMatrix(page, marker, liveLlmAvailable) {
  await closeRunPanel(page)
  await assertNodeCannotRunStandalone(page, '.coze-node.node-start')
  await assertNodeCannotRunStandalone(page, '.coze-node.node-condition')
  await runSelectedNode(page, '.coze-node.node-knowledge', {}, `KB_SIX_NODE_${marker}`)
  if (liveLlmAvailable) {
    await runSelectedNode(page, '.coze-node.node-llm', { 'kb.answer': 'KB fixture' }, `LLM_MATRIX_${marker}`)
  }
  await runSelectedNode(page, '.coze-node.node-api_call', { 'llm.answer': `LLM_MATRIX_${marker}` }, 'API_REAL: POST /text/')
  await assertNodeCannotRunStandalone(page, '.coze-node.node-end')
}

const browser = await chromium.launch({
  headless: process.env.HIFY_E2E_HEADED !== '1',
  slowMo: process.env.HIFY_E2E_HEADED === '1' ? 120 : 0,
})
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let localApi

try {
  const marker = `SN_${Date.now()}`
  if (invalidConfigOnly) {
    await runInvalidConfigReadableError(page, marker)
    console.log('PASS workflow six-node matrix invalid-config readable error e2e')
  } else {
    localApi = await startLocalApiServer()
    const modelConfigId = await findOpenRouterQwenModel(page)
    assert(modelConfigId, 'OpenRouter qwen/qwen3.5-9b model config is required for six-node matrix UAT')
    const kb = await createKnowledgeBase(page, marker)
    const apiResource = await createApiResource(page, marker, localApi.url)
    const workflow = await createFlow(
      page,
      graphPayload({
        name: `Workflow Six Node Matrix ${marker}`,
        flowType: 'WORKFLOW',
        kbId: kb.id,
        marker,
        startVariable: 'USER_INPUT',
        apiResourceId: apiResource.id,
        modelConfigId,
      }),
      false,
    )
    const workflowLiveLlm = await probeFullChainApi(page, workflow, marker, false)
    await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
    if (workflowLiveLlm) {
      await runWorkflowFullChain(page, marker)
    }
    await runWorkflowSelectedNodeMatrix(page, marker, workflowLiveLlm)
    if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })

    const chatflow = await createFlow(
      page,
      graphPayload({
        name: `Chatflow Six Node Matrix ${marker}`,
        flowType: 'CHATFLOW',
        kbId: kb.id,
        marker,
        startVariable: 'sys.query',
        apiResourceId: apiResource.id,
        modelConfigId,
      }),
      true,
    )
    const chatflowLiveLlm = await probeFullChainApi(page, chatflow, marker, true)
    await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
    if (chatflowLiveLlm) {
      await runChatflowFullChain(page, marker)
    }
    if (chatflowScreenshotPath) await page.screenshot({ path: chatflowScreenshotPath, fullPage: true })

    console.log('PASS workflow/chatflow six-node matrix e2e')
  }
} finally {
  if (localApi) await localApi.close()
  await browser.close()
}
