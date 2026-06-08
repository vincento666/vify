import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function createPublishedChild(page, stamp) {
  const child = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `017.4 Child ${stamp}`,
      description: 'execute workflow child e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['ticket'], ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'text_process_1',
          type: 'TEXT_PROCESS',
          name: '文本处理',
          config: {
            operation: 'format_template',
            template: 'child handled {{start.ticket}}',
            outputParameters: [{ name: 'summary', type: 'string' }],
            ui: { position: { x: 500, y: 180 } },
          },
        },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: { outputVariable: 'summary', output: '{{text_process_1.summary}}', ui: { position: { x: 880, y: 180 } } },
        },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'text_process_1', condition: null },
        { sourceNodeKey: 'text_process_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create child workflow')
  return unwrap(await page.request.put(`${baseUrl}/api/v1/workflows/${child.id}`, {
    data: {
      name: child.name,
      description: child.description,
      status: 'PUBLISHED',
      nodes: child.nodes,
      edges: child.edges,
    },
  }), 'publish child workflow')
}

async function createParent(page, stamp, childId) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `017.4 Parent ${stamp}`,
      description: 'execute workflow parent e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['ticket'], ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'execute_workflow_1',
          type: 'EXECUTE_WORKFLOW',
          name: '工作流',
          config: {
            targetWorkflowId: childId,
            inputMappings: [
              { name: 'ticket', valueMode: 'reference', value: '{{start.ticket}}', required: true },
            ],
            outputMappings: [
              { source: 'summary', target: 'childSummary' },
            ],
            timeoutMs: 30000,
            maxDepth: 3,
            outputParameters: [
              { name: 'childSummary', type: 'string' },
              { name: 'nestedRunId', type: 'number' },
              { name: 'status', type: 'string' },
              { name: 'latencyMs', type: 'number' },
              { name: 'mappedInputSummary', type: 'object' },
              { name: 'mappedOutputSummary', type: 'object' },
              { name: 'error', type: 'string' },
            ],
            ui: { position: { x: 500, y: 180 } },
          },
        },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: { outputVariable: 'final', output: 'parent received {{execute_workflow_1.childSummary}}', ui: { position: { x: 880, y: 180 } } },
        },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'execute_workflow_1', condition: null },
        { sourceNodeKey: 'execute_workflow_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create parent workflow')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()
  const child = await createPublishedChild(page, stamp)
  const parent = await createParent(page, stamp, child.id)

  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${parent.id}/runs`, {
    data: { input: { ticket: 'A-451' } },
  }), 'run parent workflow')
  assert(run.status === 'SUCCEEDED', 'Expected parent workflow success')
  assert(run.output.final === 'parent received child handled A-451', 'Expected child output mapped downstream')

  await page.goto(`${baseUrl}/workflows/${parent.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByLabel('添加节点').click()
  const palette = page.locator('[data-testid="bottom-node-palette"]')
  await palette.waitFor({ state: 'visible', timeout: 10000 })
  assert((await palette.innerText()).includes('工作流'), 'Expected execute workflow entry visible in node palette')
  await page.getByLabel('添加节点').click()

  const executeNode = page.locator('.coze-node.node-execute_workflow')
  await executeNode.waitFor({ state: 'visible', timeout: 10000 })
  await executeNode.click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  const panelText = await panel.innerText()
  assert(panelText.includes('工作流'), 'Expected subworkflow resource selector section')
  assert(panelText.includes('参数映射'), 'Expected schema mapping config section')
  assert(!panelText.includes('目标工作流 ID'), 'Subworkflow panel should not expose legacy targetWorkflowId field')
  assert(!panelText.includes('输入映射'), 'Subworkflow panel should use schema mapping copy instead of legacy input mapping')
  assert(!panelText.includes('输出映射'), 'Subworkflow panel should not expose legacy output mapping in the basic panel')
  assert(!panelText.includes('最大嵌套深度'), 'Subworkflow panel should not expose compatibility max depth field')
  assert(await panel.locator('[data-testid="tool-call-resource-select"]').count() >= 1, 'Expected resource selector field')
  assert(await panel.locator('[data-testid="schema-input-mapping-editor"]').count() === 1, 'Expected schema input mapping editor')

  await panel.getByRole('button', { name: '试运行当前节点', exact: true }).click()
  const drawer = page.locator('[data-testid="node-test-drawer"]')
  await drawer.waitFor({ state: 'visible', timeout: 10000 })
  await drawer.locator('.node-test-input-row', { hasText: 'ticket' }).locator('input').fill('B-452')
  await drawer.getByRole('button', { name: '运行', exact: true }).click()
  await drawer.locator('.node-test-status.success').waitFor({ state: 'visible', timeout: 10000 })
  const drawerText = await drawer.innerText()
  assert(drawerText.includes('child handled B-452'), 'Expected selected node mapped child output')
  assert(drawerText.includes('nestedRunId'), 'Expected selected node nested run evidence')
  assert(drawerText.includes('latencyMs'), 'Expected selected node nested latency evidence')
  assert(drawerText.includes('mappedInputSummary'), 'Expected selected node mapped input evidence')
  assert(drawerText.includes('mappedOutputSummary'), 'Expected selected node mapped output evidence')
  assert(drawerText.includes('SUCCEEDED'), 'Expected selected node success status')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS workflow execute workflow node e2e parent=${parent.id} child=${child.id}`)
} finally {
  await browser.close()
}
