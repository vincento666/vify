import http from 'node:http'
import { mkdir, writeFile } from 'node:fs/promises'

const defaultBaseUrl = 'http://127.0.0.1:5173'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function request(baseUrl, path, options = {}, label = path) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: options.headers || (options.body ? { 'content-type': 'application/json' } : undefined),
    ...options,
  })
  const text = await response.text()
  let payload = {}
  try {
    payload = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`${label} returned non-JSON HTTP ${response.status}: ${text}`)
  }
  assert(response.ok, `${label} HTTP ${response.status}: ${text}`)
  assert(payload.code === 200, `${label} API ${payload.message || text}`)
  return payload.data
}

async function postJson(baseUrl, path, data, label) {
  return request(baseUrl, path, { method: 'POST', body: JSON.stringify(data) }, label)
}

async function putJson(baseUrl, path, data, label) {
  return request(baseUrl, path, { method: 'PUT', body: JSON.stringify(data) }, label)
}

async function getJson(baseUrl, path, label) {
  return request(baseUrl, path, { method: 'GET' }, label)
}

async function startLocalApiServer() {
  const server = http.createServer((req, res) => {
    if (req.url?.startsWith('/echo/')) {
      res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' })
      res.end(`API_REAL: ${req.method} ${req.url}`)
      return
    }
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' })
    res.end('not found')
  })
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  assert(address && typeof address === 'object', 'Expected local API server address')
  return {
    url: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  }
}

async function findOpenRouterQwenModel(baseUrl) {
  for (let page = 1; page <= 20; page += 1) {
    const providers = await getJson(baseUrl, `/api/v1/providers?page=${page}&pageSize=100`, 'list providers')
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      if (String(provider.baseUrl || '') !== 'https://openrouter.ai/api/v1') continue
      for (const model of provider.models ?? []) {
        if (model.enabled && String(model.modelId || '') === 'qwen/qwen3.5-9b') {
          return model.id
        }
      }
    }
    if ((providers.list ?? []).length === 0 || page * 100 >= providers.total) break
  }
  throw new Error('OpenRouter qwen/qwen3.5-9b model config is required for visible chatflow UAT')
}

async function createKnowledgeBase(baseUrl, marker) {
  const kb = await postJson(
    baseUrl,
    '/api/v1/knowledge-bases',
    { name: `In-app visible UAT KB ${marker}`, description: 'visible browser chatflow UAT' },
    'create knowledge base',
  )
  const document = await request(
    baseUrl,
    `/api/v1/knowledge-bases/${kb.id}/documents`,
    multipartTextFile(
      `inapp-visible-${marker}.txt`,
      `Knowledge marker ${marker}. Approved answer is KB_VISIBLE_${marker}.`,
    ),
    'upload knowledge document',
  )
  for (let index = 0; index < 30; index += 1) {
    const latest = await getJson(baseUrl, `/api/v1/documents/${document.id}`, 'get knowledge document')
    if (latest.status === 'DONE') return kb
    assert(latest.status !== 'FAILED', `knowledge document failed: ${latest.errorMessage || ''}`)
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error('knowledge document did not finish processing')
}

function multipartTextFile(filename, content) {
  const boundary = `----hify-visible-uat-${Date.now()}-${Math.random().toString(16).slice(2)}`
  const body = [
    `--${boundary}`,
    `Content-Disposition: form-data; name="file"; filename="${filename}"`,
    'Content-Type: text/plain; charset=utf-8',
    '',
    content,
    `--${boundary}--`,
    '',
  ].join('\r\n')
  return {
    method: 'POST',
    headers: { 'content-type': `multipart/form-data; boundary=${boundary}` },
    body,
  }
}

async function createPublishedChildWorkflow(baseUrl, stamp) {
  const child = await postJson(baseUrl, '/api/v1/workflows', {
    name: `In-app Child ${stamp}`,
    description: 'visible chatflow execute workflow child',
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
  }, 'create child workflow')
  return putJson(baseUrl, `/api/v1/workflows/${child.id}`, {
    name: child.name,
    description: child.description,
    status: 'PUBLISHED',
    nodes: child.nodes,
    edges: child.edges,
  }, 'publish child workflow')
}

function chatflowPayload(name, nodes, edges) {
  return { name, description: 'visible in-app Browser output UAT', nodes, edges }
}

async function createChatflow(baseUrl, name, nodes, edges) {
  return postJson(baseUrl, '/api/v1/chatflows', chatflowPayload(name, nodes, edges), `create ${name}`)
}

async function createFixtures(baseUrl) {
  const stamp = Date.now()
  const modelConfigId = await findOpenRouterQwenModel(baseUrl)
  const apiServer = await startLocalApiServer()
  const kb = await createKnowledgeBase(baseUrl, stamp)
  const child = await createPublishedChildWorkflow(baseUrl, stamp)
  const mcp = await postJson(
    baseUrl,
    '/api/v1/mcp-servers',
    { name: `In-app Visible Tool MCP ${stamp}`, endpoint: 'mock://tools', description: 'visible UAT tool call' },
    'create mcp server',
  )
  const agentMarker = `AGENT_VISIBLE_${stamp}`
  const agent = await postJson(baseUrl, '/api/v1/agents', {
    name: `In-app Visible Agent ${stamp}`,
    description: 'visible browser agent call target',
    systemPrompt: `Reply exactly with ${agentMarker}.`,
    modelConfigId,
    temperature: 0,
    maxTokens: 64,
    maxContextTurns: 4,
    toolIds: [],
  }, 'create agent')

  const cases = []
  const baseStart = { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 120, y: 180 } } } }

  cases.push({
    key: 'message_condition',
    title: 'MESSAGE + CONDITION + END',
    message: 'vip customer',
    expected: `VIP_VISIBLE_${stamp}`,
    chatflow: await createChatflow(baseUrl, `In-app MESSAGE CONDITION ${stamp}`, [
      baseStart,
      {
        nodeKey: 'condition_1',
        type: 'CONDITION',
        name: '条件',
        config: {
          conditionBranches: [{ key: 'vip', conditions: [{ left: '{{start.sys.query}}', operator: 'contains', right: 'vip' }] }],
          defaultBranch: 'normal',
          outputVariable: 'route',
          ui: { position: { x: 440, y: 180 } },
        },
      },
      { nodeKey: 'vip_msg', type: 'MESSAGE', name: 'VIP', config: { content: `VIP_VISIBLE_${stamp}`, outputVariable: 'content', ui: { position: { x: 760, y: 100 } } } },
      { nodeKey: 'normal_msg', type: 'MESSAGE', name: 'Normal', config: { content: 'NORMAL_SHOULD_NOT_APPEAR', outputVariable: 'content', ui: { position: { x: 760, y: 300 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{vip_msg.content}}{{normal_msg.content}}', ui: { position: { x: 1080, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'condition_1', condition: null },
      { sourceNodeKey: 'condition_1', targetNodeKey: 'vip_msg', condition: 'vip' },
      { sourceNodeKey: 'condition_1', targetNodeKey: 'normal_msg', condition: null },
      { sourceNodeKey: 'vip_msg', targetNodeKey: 'end', condition: null },
      { sourceNodeKey: 'normal_msg', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'intent_recognition',
    title: 'INTENT_RECOGNITION + branch END',
    message: '我要退款',
    expected: `INTENT_REFUND_${stamp}`,
    chatflow: await createChatflow(baseUrl, `In-app INTENT ${stamp}`, [
      baseStart,
      {
        nodeKey: 'intent_1',
        type: 'INTENT_RECOGNITION',
        name: '意图识别',
        config: {
          inputSource: '{{start.sys.query}}',
          outputVariable: 'intent',
          classifierMode: 'fake',
          defaultIntent: 'default',
          intents: [
            { key: 'refund', name: '退款', description: '退款售后', examples: ['退款', '售后'] },
            { key: 'shipping', name: '物流', description: '物流快递', examples: ['物流', '快递'] },
          ],
          ui: { position: { x: 460, y: 180 } },
        },
      },
      { nodeKey: 'refund_msg', type: 'MESSAGE', name: '退款', config: { content: `INTENT_REFUND_${stamp}`, outputVariable: 'content', ui: { position: { x: 820, y: 80 } } } },
      { nodeKey: 'shipping_msg', type: 'MESSAGE', name: '物流', config: { content: 'SHIPPING_SHOULD_NOT_APPEAR', outputVariable: 'content', ui: { position: { x: 820, y: 240 } } } },
      { nodeKey: 'default_msg', type: 'MESSAGE', name: '默认', config: { content: 'DEFAULT_SHOULD_NOT_APPEAR', outputVariable: 'content', ui: { position: { x: 820, y: 400 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{refund_msg.content}}{{shipping_msg.content}}{{default_msg.content}}', ui: { position: { x: 1160, y: 240 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'intent_1', condition: null },
      { sourceNodeKey: 'intent_1', targetNodeKey: 'refund_msg', condition: 'refund' },
      { sourceNodeKey: 'intent_1', targetNodeKey: 'shipping_msg', condition: 'shipping' },
      { sourceNodeKey: 'intent_1', targetNodeKey: 'default_msg', condition: null },
      { sourceNodeKey: 'refund_msg', targetNodeKey: 'end', condition: null },
      { sourceNodeKey: 'shipping_msg', targetNodeKey: 'end', condition: null },
      { sourceNodeKey: 'default_msg', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'transform_variables',
    title: 'TEXT_PROCESS + JSON_PARSE + VARIABLE_AGGREGATION + VARIABLE_ASSIGN',
    message: '  Ada  ',
    expected: `route=gold name=Ada`,
    chatflow: await createChatflow(baseUrl, `In-app TRANSFORM VARIABLES ${stamp}`, [
      baseStart,
      { nodeKey: 'trim_1', type: 'TEXT_PROCESS', name: 'Trim', config: { operation: 'trim', source: '{{start.sys.query}}', outputVariable: 'name', ui: { position: { x: 420, y: 180 } } } },
      { nodeKey: 'json_1', type: 'JSON_PARSE', name: 'JSON', config: { sourceValue: '{"tier":"gold"}', outputVariable: 'parsed', ui: { position: { x: 680, y: 180 } } } },
      {
        nodeKey: 'aggregate_1',
        type: 'VARIABLE_AGGREGATION',
        name: '聚合',
        config: {
          strategy: 'first_non_empty',
          sources: [{ name: 'primary', value: 'gold' }, { name: 'fallback', value: 'standard' }],
          outputVariable: 'selected',
          ui: { position: { x: 940, y: 180 } },
        },
      },
      { nodeKey: 'assign_1', type: 'VARIABLE_ASSIGN', name: '赋值', config: { targetScope: 'flow', targetVariable: 'route', source: '{{aggregate_1.selected}}', writeMode: 'set', ui: { position: { x: 1200, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'route={{flow.route}} name={{trim_1.name}}', ui: { position: { x: 1460, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'trim_1', condition: null },
      { sourceNodeKey: 'trim_1', targetNodeKey: 'json_1', condition: null },
      { sourceNodeKey: 'json_1', targetNodeKey: 'aggregate_1', condition: null },
      { sourceNodeKey: 'aggregate_1', targetNodeKey: 'assign_1', condition: null },
      { sourceNodeKey: 'assign_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'llm_real_qwen',
    title: 'LLM real OpenRouter qwen/qwen3.5-9b',
    message: `LLM_VISIBLE_${stamp}`,
    expected: `LLM_VISIBLE_${stamp}`,
    chatflow: await createChatflow(baseUrl, `In-app LLM ${stamp}`, [
      baseStart,
      {
        nodeKey: 'llm_1',
        type: 'LLM',
        name: '大模型',
        config: {
          modelConfigId,
          prompt: 'Reply exactly this token and nothing else: {{start.sys.query}}',
          outputVariable: 'answer',
          temperature: 0,
          maxTokens: 64,
          ui: { position: { x: 480, y: 180 } },
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{llm_1.answer}}', ui: { position: { x: 840, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
      { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'agent_call_real_qwen',
    title: 'AGENT_CALL real OpenRouter-backed agent',
    message: 'hello agent',
    expected: agentMarker,
    chatflow: await createChatflow(baseUrl, `In-app AGENT ${stamp}`, [
      baseStart,
      {
        nodeKey: 'agent_call_1',
        type: 'AGENT_CALL',
        name: '智能体',
        config: {
          targetAgentId: agent.id,
          inputMappings: [{ name: 'message', valueMode: 'literal', value: `Reply exactly with ${agentMarker}.`, required: true }],
          outputMappings: [{ source: 'answer', target: 'agentAnswer' }],
          timeoutMs: 60000,
          maxDepth: 3,
          ui: { position: { x: 500, y: 180 } },
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{agent_call_1.agentAnswer}}', ui: { position: { x: 880, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'agent_call_1', condition: null },
      { sourceNodeKey: 'agent_call_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'knowledge',
    title: 'KNOWLEDGE + MESSAGE',
    message: `Knowledge marker ${stamp}`,
    expected: `KB_VISIBLE_${stamp}`,
    chatflow: await createChatflow(baseUrl, `In-app KNOWLEDGE ${stamp}`, [
      baseStart,
      { nodeKey: 'knowledge_1', type: 'KNOWLEDGE', name: '知识库', config: { query: '{{start.sys.query}}', knowledgeBaseId: kb.id, topK: 2, outputVariable: 'answer', ui: { position: { x: 480, y: 180 } } } },
      { nodeKey: 'message_1', type: 'MESSAGE', name: '消息', config: { content: 'KB {{knowledge_1.answer}}', outputVariable: 'content', ui: { position: { x: 820, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{message_1.content}}', ui: { position: { x: 1160, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'knowledge_1', condition: null },
      { sourceNodeKey: 'knowledge_1', targetNodeKey: 'message_1', condition: null },
      { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'api_call',
    title: 'API_CALL + END',
    message: `API-${stamp}`,
    expected: `API_REAL: POST /echo/API-${stamp}`,
    chatflow: await createChatflow(baseUrl, `In-app API CALL ${stamp}`, [
      baseStart,
      { nodeKey: 'api_1', type: 'API_CALL', name: 'API 调用', config: { method: 'POST', endpoint: `${apiServer.url}/echo/{{start.sys.query}}`, outputVariable: 'response', ui: { position: { x: 500, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{api_1.response}}', ui: { position: { x: 860, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'api_1', condition: null },
      { sourceNodeKey: 'api_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'tool_call',
    title: 'TOOL_CALL mock MCP',
    message: 'A-300',
    expected: 'Order A-300 status: SHIPPED',
    chatflow: await createChatflow(baseUrl, `In-app TOOL CALL ${stamp}`, [
      baseStart,
      {
        nodeKey: 'tool_call_1',
        type: 'TOOL_CALL',
        name: '工具调用',
        config: {
          resourceType: 'MCP_TOOL',
          resourceId: `mcp:${mcp.id}:lookup_order`,
          serverIds: [mcp.id],
          toolName: 'lookup_order',
          inputMappings: [{ name: 'orderId', valueMode: 'reference', value: '{{start.sys.query}}', required: true }],
          outputParameters: [{ name: 'result', type: 'string' }],
          ui: { position: { x: 500, y: 180 } },
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{tool_call_1.result}}', ui: { position: { x: 860, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'tool_call_1', condition: null },
      { sourceNodeKey: 'tool_call_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'execute_workflow',
    title: 'EXECUTE_WORKFLOW child workflow',
    message: 'C-453',
    expected: '客服结果 child handled C-453',
    chatflow: await createChatflow(baseUrl, `In-app EXECUTE WORKFLOW ${stamp}`, [
      baseStart,
      {
        nodeKey: 'execute_workflow_1',
        type: 'EXECUTE_WORKFLOW',
        name: '工作流',
        config: {
          targetWorkflowId: child.id,
          inputMappings: [{ name: 'ticket', valueMode: 'reference', value: '{{start.sys.query}}', required: true }],
          outputMappings: [{ source: 'summary', target: 'childSummary' }],
          maxDepth: 3,
          outputParameters: [
            { name: 'childSummary', type: 'string' },
            { name: 'nestedRunId', type: 'number' },
            { name: 'status', type: 'string' },
          ],
          ui: { position: { x: 500, y: 180 } },
        },
      },
      { nodeKey: 'message_1', type: 'MESSAGE', name: '消息', config: { outputVariable: 'content', content: '客服结果 {{execute_workflow_1.childSummary}}', ui: { position: { x: 880, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{message_1.content}}', ui: { position: { x: 1220, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'execute_workflow_1', condition: null },
      { sourceNodeKey: 'execute_workflow_1', targetNodeKey: 'message_1', condition: null },
      { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'question_resume',
    title: 'QUESTION + VARIABLE_ASSIGN resume',
    message: 'start',
    expected: '主题？',
    resumeValue: 'refund',
    resumeExpected: 'topic=refund',
    chatflow: await createChatflow(baseUrl, `In-app QUESTION RESUME ${stamp}`, [
      baseStart,
      { nodeKey: 'question_1', type: 'QUESTION', name: '问题', config: { question: '主题？', outputVariable: 'answer', ui: { position: { x: 460, y: 180 } } } },
      { nodeKey: 'assign_1', type: 'VARIABLE_ASSIGN', name: '变量赋值', config: { targetScope: 'conversation', targetVariable: 'topic', source: '{{question_1.answer}}', ui: { position: { x: 780, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'topic={{conversation.topic}}', ui: { position: { x: 1120, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'question_1', condition: null },
      { sourceNodeKey: 'question_1', targetNodeKey: 'assign_1', condition: null },
      { sourceNodeKey: 'assign_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'information_collection',
    title: 'INFORMATION_COLLECTION interrupt/resume',
    message: '我叫 Ada',
    expected: '手机号',
    resumeValue: '手机号: 13800138000',
    resumeExpected: 'name=Ada phone=13800138000',
    chatflow: await createChatflow(baseUrl, `In-app INFO COLLECTION ${stamp}`, [
      baseStart,
      {
        nodeKey: 'collect_1',
        type: 'INFORMATION_COLLECTION',
        name: '信息收集',
        config: {
          inputSource: '{{start.sys.query}}',
          outputVariable: 'profile',
          collectionKey: 'profile',
          extractorMode: 'fake',
          includeHistory: true,
          fields: [
            { name: 'name', type: 'string', required: true, description: '姓名' },
            { name: 'phone', type: 'string', required: true, description: '手机号' },
          ],
          ui: { position: { x: 460, y: 180 } },
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'name={{collect_1.name}} phone={{collect_1.phone}}', ui: { position: { x: 840, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'collect_1', condition: null },
      { sourceNodeKey: 'collect_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'transfer_to_human',
    title: 'TRANSFER_TO_HUMAN interrupt',
    message: '转人工',
    expected: '已为你转接 VIP 人工客服，请稍候。',
    interrupted: true,
    chatflow: await createChatflow(baseUrl, `In-app TRANSFER HUMAN ${stamp}`, [
      baseStart,
      {
        nodeKey: 'transfer_to_human_1',
        type: 'TRANSFER_TO_HUMAN',
        name: '转人工',
        config: {
          message: '已为你转接 VIP 人工客服，请稍候。',
          queue: 'vip-support',
          reason: 'vip_escalation',
          priority: 'high',
          ui: { position: { x: 500, y: 180 } },
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'handoff={{transfer_to_human_1.handoff_status}}', ui: { position: { x: 860, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'transfer_to_human_1', condition: null },
      { sourceNodeKey: 'transfer_to_human_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  return { stamp, apiServer, cases }
}

async function ensureVisibleBrowser(browser) {
  await (await browser.capabilities.get('visibility')).set(true)
  let tab
  try {
    tab = await browser.tabs.selected()
  } catch {
    tab = undefined
  }
  if (!tab) tab = await browser.tabs.new()
  return tab
}

async function unique(locator, label) {
  const count = await locator.count()
  assert(count === 1, `${label} expected exactly 1 element, got ${count}`)
  return locator
}

async function uniqueRoleButtonByNames(scope, names, label) {
  const matches = []
  for (const name of names) {
    const locator = scope.getByRole('button', { name, exact: true })
    const count = await locator.count()
    for (let index = 0; index < count; index += 1) {
      const button = locator.nth(index)
      if (await button.isVisible().catch(() => false)) {
        matches.push({ name, button })
      }
    }
  }
  const preferred = [...matches].reverse().find((match) => match.name === '试运行') || matches[0]
  assert(preferred, `${label} expected at least one visible button among ${names.join(', ')}, got 0`)
  return preferred.button
}

async function readUiState(tab) {
  return tab.playwright.evaluate(() => ({
    messages: Array.from(document.querySelectorAll('[data-testid="chatflow-assistant-message"]')).map((item) => item.textContent || ''),
    status: Array.from(document.querySelectorAll('[data-testid="test-run-panel"] *')).map((item) => item.textContent || '').join('\n'),
    dock: Array.from(document.querySelectorAll('[data-testid="workflow-debug-dock"] *')).map((item) => item.textContent || '').join('\n'),
  }), undefined, { timeoutMs: 5000 })
}

async function waitForVisibleText(tab, expected, options = {}) {
  const timeoutMs = options.timeoutMs || 90000
  const source = options.source || 'any'
  const deadline = Date.now() + timeoutMs
  let latest = null
  while (Date.now() < deadline) {
    latest = await readUiState(tab)
    const haystack = [
      ...(source === 'messages' || source === 'any' ? latest.messages : []),
      source === 'status' || source === 'any' ? latest.status : '',
      source === 'dock' || source === 'any' ? latest.dock : '',
    ].join('\n')
    if (haystack.includes(expected)) return { latest, haystack }
    if (haystack.includes('暂无回复内容')) {
      throw new Error(`Unexpected empty reply placeholder while waiting for ${expected}: ${haystack}`)
    }
    await tab.playwright.waitForTimeout(500)
  }
  throw new Error(`Timed out waiting for visible text ${expected}; latest=${JSON.stringify(latest)}`)
}

async function screenshot(tab, path) {
  const bytes = await tab.screenshot({ fullPage: true })
  await writeFile(path, bytes)
}

async function runChatflowInVisibleUi(tab, baseUrl, testCase, index, outputDir) {
  await tab.goto(`${baseUrl}/chatflows/${testCase.chatflow.id}/canvas`)
  await tab.playwright.waitForLoadState({ state: 'load', timeoutMs: 30000 }).catch(() => undefined)
  await tab.playwright.getByText(testCase.chatflow.name, { exact: false }).waitFor({ state: 'visible', timeoutMs: 30000 })

  const runButton = await uniqueRoleButtonByNames(tab.playwright, ['对话试运行', '试运行'], `${testCase.key} run button`)
  await runButton.click({})
  const panel = await unique(tab.playwright.getByTestId('test-run-panel'), `${testCase.key} run panel`)
  await panel.waitFor({ state: 'visible', timeoutMs: 15000 })
  const input = await unique(panel.getByTestId('chatflow-run-message-input'), `${testCase.key} message input`)
  await input.fill(testCase.message, {})
  const send = await unique(panel.getByRole('button', { name: '发送消息', exact: true }), `${testCase.key} send button`)
  await send.click({})

  const initial = await waitForVisibleText(tab, testCase.expected, { source: 'any', timeoutMs: 120000 })
  let finalText = initial.haystack

  if (testCase.resumeValue) {
    let resumeScope = panel.getByTestId('chatflow-run-resume-card')
    if (testCase.resumeViaDebugDock) {
      const runIdMatch = finalText.match(/Run #(\d+)/)
      assert(runIdMatch, `${testCase.key} could not find runtime run id before resume`)
      await tab.goto(`${baseUrl}/chatflows/${testCase.chatflow.id}/canvas?debug=1&runId=${runIdMatch[1]}&runtime=v2`)
      await tab.playwright.waitForLoadState({ state: 'load', timeoutMs: 30000 }).catch(() => undefined)
      await tab.playwright.getByTestId('workflow-debug-dock').waitFor({ state: 'visible', timeoutMs: 30000 })
      resumeScope = tab.playwright.getByTestId('workflow-debug-dock')
    }
    await resumeScope.waitFor({ state: 'visible', timeoutMs: 15000 })
    const replyInput = await unique(resumeScope.locator('input, textarea').first(), `${testCase.key} resume input`)
    await replyInput.fill(testCase.resumeValue, { timeoutMs: 5000 })
    const submit = await unique(resumeScope.getByRole('button', { name: '提交回复继续', exact: true }), `${testCase.key} resume submit`)
    await submit.click({ force: true, timeoutMs: 5000 })
    const resumed = await waitForVisibleText(tab, testCase.resumeExpected, { source: 'any', timeoutMs: 60000 })
    finalText = resumed.haystack
  }

  if (testCase.interrupted) {
    await waitForVisibleText(tab, 'INTERRUPTED', { source: 'status', timeoutMs: 15000 })
  }

  const path = `${outputDir}/inapp-chatflow-visible-uat-${String(index + 1).padStart(2, '0')}-${testCase.key}.png`
  await screenshot(tab, path)
  return {
    key: testCase.key,
    title: testCase.title,
    chatflowId: testCase.chatflow.id,
    expected: testCase.resumeExpected || testCase.expected,
    passed: true,
    screenshot: path,
    outputPreview: finalText.slice(0, 500),
  }
}

export async function runInAppChatflowVisibleOutputUat(options = {}) {
  const browser = options.browser || globalThis.browser
  assert(browser, 'in-app Browser is required')
  const baseUrl = options.baseUrl || defaultBaseUrl
  const outputDir = options.outputDir || '/Users/vincento/work/develop/hify/output/playwright'
  await mkdir(outputDir, { recursive: true })
  const tab = options.tab || await ensureVisibleBrowser(browser)
  globalThis.tab = tab
  const fixtures = await createFixtures(baseUrl)
  const results = []
  try {
    const selectedCases = fixtures.cases
      .map((testCase, index) => ({ testCase, index }))
      .filter(({ testCase, index }) => {
        if (Array.isArray(options.onlyKeys) && !options.onlyKeys.includes(testCase.key)) return false
        if (typeof options.startAt === 'number' && index < options.startAt) return false
        if (typeof options.endBefore === 'number' && index >= options.endBefore) return false
        return true
      })
    for (const { testCase, index } of selectedCases) {
      const result = await runChatflowInVisibleUi(tab, baseUrl, testCase, index, outputDir)
      results.push(result)
    }
  } finally {
    await fixtures.apiServer.close()
  }
  const summaryPath = `${outputDir}/inapp-chatflow-visible-uat-summary-${fixtures.stamp}.json`
  await writeFile(summaryPath, JSON.stringify({ stamp: fixtures.stamp, results }, null, 2))
  return { stamp: fixtures.stamp, summaryPath, total: results.length, passed: results.length, results }
}
