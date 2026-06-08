import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  if (!response.ok()) {
    const text = await response.text()
    throw new Error(`${label} HTTP ${response.status()}: ${text}`)
  }
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function findEnabledModel(page) {
  let fallbackModelId = null
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      for (const model of provider.models ?? []) {
        if (!model.enabled) continue
        if (String(provider.baseUrl || '').startsWith('mock://success')) return model.id
        fallbackModelId ??= model.id
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  if (fallbackModelId) return fallbackModelId
  throw new Error('No enabled model found for AGENT_CALL e2e')
}

async function createAgent(page, marker) {
  const modelConfigId = await findEnabledModel(page)
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Agent Call Target ${marker}`,
        description: 'workflow agent call e2e target',
        systemPrompt:
          `You are an integration target. Always include the exact marker ${marker} and every ticket id or history ticket id supplied by the user.`,
        modelConfigId,
        temperature: 0,
        maxTokens: 256,
        maxContextTurns: 4,
        toolIds: [],
      },
    }),
    'create target agent',
  )
}

function agentCallFlowPayload(name, flowType, agentId, marker, historyMode = 'none') {
  const queryRef = flowType === 'CHATFLOW' ? '{{start.sys.query}}' : '{{start.ticket}}'
  const messageTemplate = flowType === 'CHATFLOW'
    ? `Marker ${marker}. Current query: {{start.sys.query}}.`
    : `Marker ${marker}. Handle ticket {{start.ticket}}.`
  return {
    name,
    description: 'agent call e2e flow',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: {} },
      {
        nodeKey: 'agent_call_1',
        type: 'AGENT_CALL',
        name: '智能体',
        config: {
          targetAgentId: agentId,
          inputMappings: [
            { name: 'message', valueMode: 'reference', value: messageTemplate, required: true },
            { name: 'query', valueMode: 'reference', value: queryRef },
          ],
          historyMode,
          outputMappings: [{ source: 'answer', target: 'agentAnswer' }],
          timeoutMs: 60000,
          maxDepth: 3,
          outputParameters: [
            { name: 'agentAnswer', type: 'string' },
            { name: 'sessionId', type: 'number' },
            { name: 'status', type: 'string' },
            { name: 'latencyMs', type: 'number' },
            { name: 'mappedInputSummary', type: 'object' },
            { name: 'mappedOutputSummary', type: 'object' },
            { name: 'toolCalls', type: 'array' },
            { name: 'error', type: 'string' },
          ],
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: { outputVariable: 'final', output: '{{agent_call_1.agentAnswer}}' },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'agent_call_1', condition: null },
      { sourceNodeKey: 'agent_call_1', targetNodeKey: 'end', condition: null },
    ],
  }
}

async function assertWorkflowAgentCall(page, agent, marker) {
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: agentCallFlowPayload(`Agent Call Workflow ${marker}`, 'WORKFLOW', agent.id, marker),
    }),
    'create workflow',
  )
  const run = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
      data: { input: { ticket: `WF-${marker}` } },
    }),
    'run workflow',
  )
  assert(run.status === 'SUCCEEDED', `workflow run should succeed: ${JSON.stringify(run)}`)
  assert(String(run.output.final).includes(marker), `workflow output should include marker: ${JSON.stringify(run.output)}`)
  assert(String(run.output.final).includes(`WF-${marker}`), `workflow output should include ticket: ${JSON.stringify(run.output)}`)

  const nodeRun = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/nodes/agent_call_1/runs`, {
      data: { input: { ticket: `NODE-${marker}` } },
    }),
    'run selected agent call node',
  )
  assert(nodeRun.output.status === 'SUCCEEDED', `selected node should succeed: ${JSON.stringify(nodeRun)}`)
  assert(nodeRun.output.sessionId > 0, `selected node should expose sessionId: ${JSON.stringify(nodeRun)}`)
  assert(String(nodeRun.output.agentAnswer).includes(marker), `selected node answer should include marker: ${JSON.stringify(nodeRun)}`)

  await page.goto(`${baseUrl}${run.debugUrl}`, { waitUntil: 'load' })
  await page.getByText('智能体').waitFor({ state: 'visible', timeout: 10000 })
  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })
  return { workflow, run }
}

async function assertChatflowAgentCall(page, agent, marker) {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: agentCallFlowPayload(`Agent Call Chatflow ${marker}`, 'CHATFLOW', agent.id, marker, 'include'),
    }),
    'create chatflow',
  )
  const run = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
      data: {
        input: {
          'sys.query': `Current ticket CF-${marker}`,
          'sys.conversation_id': `agent-call-${marker}`,
          'sys.user_id': 'agent-call-e2e',
          'sys.channel': 'web',
          history: [
            { role: 'user', content: `Previous ticket HIST-${marker}` },
            { role: 'assistant', content: 'I found the prior order.' },
          ],
        },
      },
    }),
    'run chatflow',
  )
  assert(run.status === 'SUCCEEDED', `chatflow run should succeed: ${JSON.stringify(run)}`)
  assert(String(run.output.final).includes(marker), `chatflow output should include marker: ${JSON.stringify(run.output)}`)
  assert(String(run.output.final).includes(`CF-${marker}`), `chatflow output should include current ticket: ${JSON.stringify(run.output)}`)
  assert(String(run.output.final).includes(`HIST-${marker}`), `chatflow output should include history ticket: ${JSON.stringify(run.output)}`)
  return { chatflow, run }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const marker = `AC${Date.now()}`
  const agent = await createAgent(page, marker)

  const resources = await unwrap(
    await page.request.get(`${baseUrl}/api/v1/workflow-resources?flowType=CHATFLOW`),
    'list workflow resources',
  )
  assert(
    (resources.list ?? []).some((item) => item.resourceId === `agent:${agent.id}` && item.resourceType === 'AGENT'),
    `resource registry should include target agent: ${JSON.stringify(resources)}`,
  )

  const workflowResult = await assertWorkflowAgentCall(page, agent, marker)
  const chatflowResult = await assertChatflowAgentCall(page, agent, marker)

  console.log(
    `PASS workflow agent call e2e agent=${agent.id} workflow=${workflowResult.workflow.id} chatflow=${chatflowResult.chatflow.id}`,
  )
} finally {
  await browser.close()
}
