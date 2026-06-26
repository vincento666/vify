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
      name: `022.2 Child ${stamp}`,
      description: 'chatflow subworkflow child e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['ticket'], ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'format_1',
          type: 'TEXT_PROCESS',
          name: '文本处理',
          config: {
            operation: 'format_template',
            template: 'child handled {{start.ticket}}',
            outputParameters: [{ name: 'summary', type: 'string' }],
            ui: { position: { x: 500, y: 180 } },
          },
        },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'summary', output: '{{format_1.summary}}', ui: { position: { x: 880, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'format_1', condition: null },
        { sourceNodeKey: 'format_1', targetNodeKey: 'end', condition: null },
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

async function createParentChatflow(page, stamp, childId) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `022.2 Parent Chatflow ${stamp}`,
      description: 'chatflow execute workflow e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['ticket'], ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'execute_workflow_1',
          type: 'EXECUTE_WORKFLOW',
          name: '工作流',
          config: {
            targetWorkflowId: childId,
            inputMappings: [{ name: 'ticket', valueMode: 'reference', value: '{{start.ticket}}', required: true }],
            outputMappings: [{ source: 'summary', target: 'childSummary' }],
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
        { nodeKey: 'message_1', type: 'MESSAGE', name: '消息', config: { outputVariable: 'content', content: '客服结果 {{execute_workflow_1.childSummary}}', ui: { position: { x: 880, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{message_1.content}}', ui: { position: { x: 1220, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'execute_workflow_1', condition: null },
        { sourceNodeKey: 'execute_workflow_1', targetNodeKey: 'message_1', condition: null },
        { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create parent chatflow')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()
  const child = await createPublishedChild(page, stamp)
  const chatflow = await createParentChatflow(page, stamp, child.id)
  const conversationId = `cf-exec-workflow-${stamp}`
  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs-legacy`, {
    data: {
      input: {
        ticket: 'C-453',
        'sys.query': '查询订单 C-453',
        'sys.conversation_id': conversationId,
        'sys.user_id': `user-${stamp}`,
        'sys.channel': 'web',
      },
    },
  }), 'run parent chatflow')

  assert(run.status === 'SUCCEEDED', `Expected chatflow success, got ${run.status}`)
  assert(run.output.final === '客服结果 child handled C-453', 'Expected child output mapped into message/end output')
  assert(run.debugUrl === `/chatflows/${chatflow.id}/canvas?runId=${run.runId}&debug=1`, 'Expected composer debug URL')

  const session = await unwrap(await page.request.get(`${baseUrl}/api/v1/chatflows/${chatflow.id}/sessions/${conversationId}`), 'get parent session')
  assert(session.status === 'completed', `Expected completed parent session, got ${session.status}`)
  assert(session.variables.node_outputs.execute_workflow_1.childSummary === 'child handled C-453', 'Expected parent session node output scope')

  await page.goto(`${baseUrl}${run.debugUrl}`, { waitUntil: 'networkidle' })
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByText(`Run #${run.runId}`, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  const dockText = await dock.textContent()
  assert(dockText.includes('execute_workflow_1'), 'Expected debug dock to show execute workflow node')
  assert(dockText.includes('nestedRunId'), 'Expected debug dock nestedRunId evidence')
  assert(dockText.includes('mappedInputSummary'), 'Expected debug dock mapped input evidence')
  assert(dockText.includes('mappedOutputSummary'), 'Expected debug dock mapped output evidence')
  assert(dockText.includes('child handled C-453'), 'Expected debug dock child output evidence')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS chatflow execute workflow node e2e chatflow=${chatflow.id} child=${child.id} run=${run.runId}`)
} finally {
  await browser.close()
}
