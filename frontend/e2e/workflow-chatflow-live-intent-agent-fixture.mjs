const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { 'content-type': 'application/json' },
    ...options,
  })
  if (!response.ok) throw new Error(`${options.method || 'GET'} ${path} HTTP ${response.status}: ${await response.text()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${options.method || 'GET'} ${path} API ${payload.message}`)
  return payload.data
}

async function configuredQwen() {
  for (let page = 1; page <= 20; page += 1) {
    const providers = await requestJson(`/api/v1/providers?page=${page}&pageSize=100&enabled=true`)
    for (const provider of providers.list ?? []) {
      const model = (provider.models ?? []).find((item) =>
        provider.enabled
        && provider.authConfigured
        && item.enabled
        && item.modelId === 'qwen/qwen3.5-9b',
      )
      if (model) return { providerId: provider.id, modelConfigId: model.id, modelId: model.modelId }
    }
    if ((providers.list ?? []).length === 0 || page * 100 >= providers.total) break
  }
  throw new Error('Configured qwen/qwen3.5-9b model is required for live Spec 225 UAT')
}

function flowGraph({ label, stamp, model, agentId }) {
  const isChatflow = label === 'chatflow'
  const inputRef = isChatflow ? '{{start.sys.query}}' : '{{start.userMessage}}'
  const llmMarker = `LLM_225_${label.toUpperCase()}_${stamp}`
  const agentMarker = `AGENT_225_${label.toUpperCase()}_${stamp}`
  return {
    name: `Spec 225 live ${label} ${stamp}`,
    description: 'temporary cleanable live Intent + Condition + LLM + Agent fixture',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: {
          outputVariables: isChatflow
            ? ['sys.query', 'sys.conversation_id', 'sys.user_id', 'sys.channel']
            : ['USER_INPUT'],
          ui: { position: { x: 80, y: 240 } },
        },
      },
      {
        nodeKey: 'intent_1',
        type: 'INTENT_RECOGNITION',
        name: '意图识别',
        config: {
          inputSource: inputRef,
          outputVariable: 'intent',
          classifierMode: 'llm',
          modelConfigId: model.modelConfigId,
          providerId: model.providerId,
          model: model.modelId,
          maxTokens: 16,
          temperature: 0,
          retryCount: 0,
          defaultIntent: 'default',
          intents: [
            { key: 'refund', name: '退款', description: 'refund request', examples: ['refund', 'return'] },
            { key: 'shipping', name: '物流', description: 'shipping request', examples: ['shipping', 'delivery'] },
          ],
          ui: { position: { x: 400, y: 240 } },
        },
      },
      {
        nodeKey: 'condition_1',
        type: 'CONDITION',
        name: '多条件校验',
        config: {
          outputVariable: 'route',
          conditionBranches: [
            {
              key: 'live_refund',
              name: 'Live refund',
              logic: 'AND',
              conditions: [
                { left: '{{intent_1.intent}}', operator: 'equals', right: 'refund' },
                { left: inputRef, operator: 'contains', right: 'live' },
              ],
            },
          ],
          defaultBranch: 'other',
          ui: { position: { x: 720, y: 240 } },
        },
      },
      {
        nodeKey: 'llm_1',
        type: 'LLM',
        name: '大模型',
        config: {
          modelConfigId: model.modelConfigId,
          providerId: model.providerId,
          model: model.modelId,
          prompt: `Return exactly ${llmMarker}.`,
          outputVariable: 'answer',
          temperature: 0,
          maxTokens: 32,
          retryCount: 0,
          ui: { position: { x: 1040, y: 120 } },
        },
      },
      {
        nodeKey: 'agent_call_1',
        type: 'AGENT_CALL',
        name: '智能体',
        config: {
          targetAgentId: agentId,
          inputMappings: [
            {
              name: 'message',
              valueMode: 'reference',
              value: `Reply exactly ${agentMarker}. Context: {{llm_1.answer}}`,
              required: true,
            },
          ],
          outputMappings: [{ source: 'answer', target: 'agentAnswer' }],
          streamOutput: false,
          timeoutMs: 30000,
          maxDepth: 1,
          ui: { position: { x: 1360, y: 120 } },
        },
      },
      { nodeKey: 'success_end', type: 'END', name: '成功结束', config: { outputVariable: 'final', output: '{{agent_call_1.agentAnswer}}', ui: { position: { x: 1680, y: 120 } } } },
      { nodeKey: 'shipping_end', type: 'END', name: '物流结束', config: { outputVariable: 'final', output: 'shipping', ui: { position: { x: 1040, y: 340 } } } },
      { nodeKey: 'fallback_end', type: 'END', name: '默认结束', config: { outputVariable: 'final', output: 'default', ui: { position: { x: 720, y: 480 } } } },
      { nodeKey: 'other_end', type: 'END', name: '条件默认', config: { outputVariable: 'final', output: 'other', ui: { position: { x: 1040, y: 480 } } } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'intent_1', condition: null },
      { sourceNodeKey: 'intent_1', targetNodeKey: 'condition_1', condition: 'refund' },
      { sourceNodeKey: 'intent_1', targetNodeKey: 'shipping_end', condition: 'shipping' },
      { sourceNodeKey: 'intent_1', targetNodeKey: 'fallback_end', condition: null },
      { sourceNodeKey: 'condition_1', targetNodeKey: 'llm_1', condition: 'live_refund' },
      { sourceNodeKey: 'condition_1', targetNodeKey: 'other_end', condition: null },
      { sourceNodeKey: 'llm_1', targetNodeKey: 'agent_call_1', condition: null },
      { sourceNodeKey: 'agent_call_1', targetNodeKey: 'success_end', condition: null },
    ],
    markers: { llm: llmMarker, agent: agentMarker, input: 'live refund' },
  }
}

async function createFixtures() {
  const model = await configuredQwen()
  const stamp = Date.now()
  const partial = {}
  try {
    const agent = await requestJson('/api/v1/agents', {
      method: 'POST',
      body: JSON.stringify({
        name: `Spec 225 live target ${stamp}`,
        description: 'temporary cleanable live UAT target',
        systemPrompt: 'Reply exactly with the marker requested in the user message.',
        modelConfigId: model.modelConfigId,
        temperature: 0,
        maxTokens: 32,
        maxContextTurns: 1,
        toolIds: [],
      }),
    })
    partial.agentId = agent.id
    const workflowGraph = flowGraph({ label: 'workflow', stamp, model, agentId: agent.id })
    const chatflowGraph = flowGraph({ label: 'chatflow', stamp, model, agentId: agent.id })
    const workflow = await requestJson('/api/v1/workflows', {
      method: 'POST',
      body: JSON.stringify(workflowGraph),
    })
    partial.workflowId = workflow.id
    const chatflow = await requestJson('/api/v1/chatflows', {
      method: 'POST',
      body: JSON.stringify(chatflowGraph),
    })
    partial.chatflowId = chatflow.id
    return {
      ...partial,
      model: { modelConfigId: model.modelConfigId, providerId: model.providerId, modelId: model.modelId },
      markers: { workflow: workflowGraph.markers, chatflow: chatflowGraph.markers },
    }
  } catch (error) {
    await cleanup(partial).catch(() => undefined)
    throw error
  }
}

async function cleanup(fixtures) {
  const failures = []
  for (const [id, prefix, label] of [
    [fixtures.workflowId, '/api/v1/workflows', 'workflow'],
    [fixtures.chatflowId, '/api/v1/chatflows', 'chatflow'],
    [fixtures.agentId, '/api/v1/agents', 'agent'],
  ]) {
    if (!id) continue
    try {
      await requestJson(`${prefix}/${id}`, { method: 'DELETE' })
    } catch (error) {
      failures.push(`${label}: ${error instanceof Error ? error.message : String(error)}`)
    }
  }
  assert(failures.length === 0, `Fixture cleanup failed: ${failures.join(' | ')}`)
}

if (process.env.HIFY_LIVE_UAT !== '1') {
  throw new Error('Set HIFY_LIVE_UAT=1 only after the approved live spend preflight')
}

if (process.env.HIFY_LIVE_FIXTURE_ACTION === 'cleanup') {
  const raw = process.env.HIFY_LIVE_FIXTURES || ''
  assert(raw, 'HIFY_LIVE_FIXTURES JSON is required for cleanup')
  await cleanup(JSON.parse(raw))
  console.log('CLEANED Spec 225 live fixtures')
} else {
  const fixtures = await createFixtures()
  console.log(`FIXTURES ${JSON.stringify(fixtures)}`)
}
