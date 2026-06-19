import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR || '/Users/vincento/work/develop/hify/artifacts/slices/194-workflow-chatflow-productionization-phase1/194.6'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || join(artifactDir, 'screenshots')
const reportPath = process.env.HIFY_E2E_REPORT || join(artifactDir, 'runtime-v2-phase1-production-uat.json')

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  const text = await response.text()
  let payload = {}
  try {
    payload = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`${label} returned non-JSON HTTP ${response.status()}: ${text}`)
  }
  assert(response.ok(), `${label} HTTP ${response.status()}: ${text}`)
  assert(payload.code === 200, `${label} API ${payload.message || text}`)
  return payload.data
}

async function requestJson(page, path, data, label) {
  return unwrap(
    await page.request.post(`${baseUrl}${path}`, { data }),
    label,
  )
}

async function waitForRuntime(page, runId, wanted = 'SUCCEEDED', timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs
  let latest = null
  while (Date.now() < deadline) {
    latest = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${runId}`), `get runtime run ${runId}`)
    if (latest.status === wanted) return latest
    if (['SUCCEEDED', 'FAILED', 'CANCELLED', 'INTERRUPTED'].includes(latest.status) && latest.status !== wanted) {
      throw new Error(`Expected ${wanted} for run ${runId}, got ${JSON.stringify(latest)}`)
    }
    await page.waitForTimeout(250)
  }
  throw new Error(`Timed out waiting for ${wanted} on run ${runId}; latest=${JSON.stringify(latest)}`)
}

function startInput(stamp) {
  return {
    'sys.query': `phase1-${stamp}`,
    'sys.conversation_id': `phase1-uat-${stamp}`,
    'sys.user_id': 'phase1-uat-user',
    'sys.channel': 'browser-uat',
  }
}

function simpleWorkflow(output) {
  return {
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output, ui: { position: { x: 600, y: 180 } } } },
    ],
    edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
  }
}

async function runVersionBindingUat(page, stamp) {
  const workflow = await requestJson(page, '/api/v1/workflows', {
    name: `194 Phase1 Version Binding ${stamp}`,
    description: 'phase1 immutable published version UAT',
    ...simpleWorkflow('published-v1'),
  }, 'create version workflow')
  const publishV1 = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/publish`), 'publish v1')
  await unwrap(await page.request.put(`${baseUrl}/api/v1/workflows/${workflow.id}`, {
    data: {
      name: workflow.name,
      description: workflow.description,
      status: workflow.status,
      ...simpleWorkflow('published-v2'),
    },
  }), 'update workflow draft v2')
  const publishV2 = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/publish`), 'publish v2')
  const targetedV1 = await requestJson(page, `/api/v1/workflows/${workflow.id}/published-runs`, {
    input: {},
    versionId: publishV1.id,
  }, 'run targeted v1')
  const activeV2 = await requestJson(page, `/api/v1/workflows/${workflow.id}/published-runs`, {
    input: {},
  }, 'run active v2')

  assert(targetedV1.output.final === 'published-v1', `targeted v1 drifted: ${JSON.stringify(targetedV1)}`)
  assert(activeV2.output.final === 'published-v2', `active v2 mismatch: ${JSON.stringify(activeV2)}`)
  assert(targetedV1.versionId === publishV1.id, 'targeted run should bind v1 version id')
  assert(activeV2.versionId === publishV2.id, 'active run should bind v2 version id')
  return { workflowId: workflow.id, publishV1, publishV2, targetedV1, activeV2 }
}

async function runNegativePublishValidationUat(page, stamp) {
  const apiWorkflow = await requestJson(page, '/api/v1/workflows', {
    name: `194 Phase1 Invalid API ${stamp}`,
    description: 'phase1 invalid API validation UAT',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
      { nodeKey: 'api_1', type: 'API_CALL', name: 'API', config: { ui: { position: { x: 420, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'never', ui: { position: { x: 720, y: 180 } } } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'api_1', condition: null },
      { sourceNodeKey: 'api_1', targetNodeKey: 'end', condition: null },
    ],
  }, 'create invalid API workflow')
  const apiResponse = await page.request.post(`${baseUrl}/api/v1/workflows/${apiWorkflow.id}/publish`)
  const apiPayload = await apiResponse.json()
  assert(apiResponse.status() === 400, `invalid API publish should fail HTTP 400: ${JSON.stringify(apiPayload)}`)
  const apiMessage = String(apiPayload.message || '')
  assert(apiMessage.includes('api_1 resourceId is required'), `missing API resource error: ${apiMessage}`)

  const toolWorkflow = await requestJson(page, '/api/v1/workflows', {
    name: `194 Phase1 Invalid Tool ${stamp}`,
    description: 'phase1 invalid Tool validation UAT',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
      { nodeKey: 'tool_1', type: 'TOOL_CALL', name: '工具', config: { resourceType: 'MCP_TOOL', ui: { position: { x: 420, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'never', ui: { position: { x: 720, y: 180 } } } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'tool_1', condition: null },
      { sourceNodeKey: 'tool_1', targetNodeKey: 'end', condition: null },
    ],
  }, 'create invalid Tool workflow')
  const toolResponse = await page.request.post(`${baseUrl}/api/v1/workflows/${toolWorkflow.id}/publish`)
  const toolPayload = await toolResponse.json()
  assert(toolResponse.status() === 400, `invalid Tool publish should fail HTTP 400: ${JSON.stringify(toolPayload)}`)
  const toolMessage = String(toolPayload.message || '')
  assert(toolMessage.includes('tool_1 tool resource is required') || toolMessage.includes('tool_1 resourceId is required'), `missing tool resource error: ${toolMessage}`)
  return { apiWorkflowId: apiWorkflow.id, apiMessage, toolWorkflowId: toolWorkflow.id, toolMessage }
}

async function runErrorRoutingDebugUat(page, stamp) {
  const chatflow = await requestJson(page, '/api/v1/chatflows', {
    name: `194 Phase1 Runtime V2 Error Routing ${stamp}`,
    description: 'phase1 runtime v2 error branch and debug evidence UAT',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 220 } } } },
      {
        nodeKey: 'code_1',
        type: 'CODE',
        name: '代码失败',
        config: {
          language: 'python',
          code: 'result = 1 / 0',
          errorBehavior: 'branch',
          outputParameters: [
            { name: 'success', type: 'boolean' },
            { name: 'error', type: 'string' },
            { name: 'evidence', type: 'object' },
          ],
          ui: { position: { x: 430, y: 220 } },
        },
      },
      { nodeKey: 'error_msg', type: 'MESSAGE', name: '错误分支', config: { content: 'error route: {{code_1.error}}', outputVariable: 'content', ui: { position: { x: 760, y: 100 } } } },
      { nodeKey: 'success_msg', type: 'MESSAGE', name: '成功分支', config: { content: 'success route', outputVariable: 'content', ui: { position: { x: 760, y: 340 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{error_msg.content}}{{success_msg.content}}', ui: { position: { x: 1080, y: 220 } } } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'code_1', condition: null },
      { sourceNodeKey: 'code_1', targetNodeKey: 'error_msg', condition: 'error' },
      { sourceNodeKey: 'code_1', targetNodeKey: 'success_msg', condition: 'success' },
      { sourceNodeKey: 'error_msg', targetNodeKey: 'end', condition: null },
      { sourceNodeKey: 'success_msg', targetNodeKey: 'end', condition: null },
    ],
  }, 'create error routing chatflow')
  const started = await requestJson(page, `/api/v1/chatflows/${chatflow.id}/runs-v2`, {
    input: startInput(stamp),
    idempotencyKey: `phase1-error-${stamp}`,
  }, 'start error routing v2 run')
  const terminal = await waitForRuntime(page, started.runId)
  assert(terminal.output.final === 'error route: division by zero', `unexpected error branch output: ${JSON.stringify(terminal)}`)
  const nodes = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${started.runId}/nodes`), 'list runtime nodes')
  const codeNode = nodes.list.find((node) => node.nodeKey === 'code_1')
  assert(codeNode?.outputs?.route === 'error', `code node should route error: ${JSON.stringify(codeNode)}`)
  assert(codeNode?.outputs?.evidence?.status === 'FAILED', `code evidence should mark failed: ${JSON.stringify(codeNode)}`)
  const events = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${started.runId}/events`), 'list runtime events')
  assert(events.list.some((event) => event.type === 'workflow_node_error_handled'), `missing handled error event: ${JSON.stringify(events)}`)

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas?debug=1&runId=${started.runId}&runtime=v2`, { waitUntil: 'networkidle' })
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByText('code_1', { exact: false }).first().waitFor({ state: 'visible', timeout: 10000 })
  await dock.getByText('division by zero', { exact: false }).first().waitFor({ state: 'visible', timeout: 10000 })
  const screenshot = join(screenshotDir, 'runtime-v2-error-debug.png')
  await page.screenshot({ path: screenshot, fullPage: true })
  return { chatflowId: chatflow.id, runId: started.runId, screenshot, terminal }
}

async function runGovernancePanelUat(page, stamp) {
  const chatflow = await requestJson(page, '/api/v1/chatflows', {
    name: `194 Phase1 Governance Panel ${stamp}`,
    description: 'phase1 API/Tool governance panel UAT',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 200 } } } },
      {
        nodeKey: 'api_1',
        type: 'API_CALL',
        name: 'API治理',
        config: {
          resourceId: 'api-resource:1',
          authMode: 'bearer',
          timeoutMs: 30000,
          retryCount: 1,
          errorBehavior: 'continue',
          headers: [],
          sensitiveHeaders: ['Authorization'],
          outputSchema: { type: 'object', properties: { result: { type: 'string' } } },
          ui: { position: { x: 430, y: 200 } },
        },
      },
      {
        nodeKey: 'tool_1',
        type: 'TOOL_CALL',
        name: '工具治理',
        config: {
          resourceType: 'MCP_TOOL',
          resourceId: 'mcp:1:lookup_order',
          serverIds: [1],
          toolName: 'lookup_order',
          timeoutMs: 30000,
          retryCount: 1,
          errorBehavior: 'branch',
          outputParameters: [{ name: 'result', type: 'string' }],
          outputSchema: { type: 'object', properties: { result: { type: 'string' } } },
          ui: { position: { x: 740, y: 200 } },
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'panel', ui: { position: { x: 1060, y: 200 } } } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'api_1', condition: null },
      { sourceNodeKey: 'api_1', targetNodeKey: 'tool_1', condition: null },
      { sourceNodeKey: 'tool_1', targetNodeKey: 'end', condition: null },
    ],
  }, 'create governance panel chatflow')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  const apiNode = page.locator('.vue-flow__node[data-id="api_1"]')
  await apiNode.waitFor({ state: 'attached', timeout: 10000 })
  await apiNode.click({ force: true })
  const panel = page.getByTestId('node-config-panel')
  const governanceSection = panel.getByTestId('resource-governance-section')
  await governanceSection.waitFor({ state: 'visible', timeout: 10000 })
  await governanceSection.getByText('调用治理', { exact: false }).waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByLabel('认证策略').first().waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByLabel('超时毫秒').first().waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByLabel('重试次数').first().waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByLabel('错误行为').first().waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByLabel('输出 Schema').first().waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByLabel('敏感 Header').first().waitFor({ state: 'visible', timeout: 10000 })
  await governanceSection.scrollIntoViewIfNeeded()
  await page.waitForTimeout(150)
  const screenshot = join(screenshotDir, 'api-tool-governance-panel.png')
  await page.screenshot({ path: screenshot, fullPage: true })
  return { chatflowId: chatflow.id, screenshot }
}

await mkdir(screenshotDir, { recursive: true })
const browser = await chromium.launch({ headless: process.env.HIFY_E2E_HEADED !== '1' })
const page = await browser.newPage({ viewport: { width: 1440, height: 940 } })

try {
  const stamp = Date.now()
  const results = {
    baseUrl,
    stamp,
    versionBinding: await runVersionBindingUat(page, stamp),
    negativePublishValidation: await runNegativePublishValidationUat(page, stamp),
    runtimeV2ErrorDebug: await runErrorRoutingDebugUat(page, stamp),
    governancePanel: await runGovernancePanelUat(page, stamp),
  }
  await writeFile(reportPath, JSON.stringify(results, null, 2))
  console.log(`PASS runtime v2 phase1 production UAT report=${reportPath}`)
} finally {
  await browser.close()
}
