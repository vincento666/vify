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

function multipartTextFile(filename, content) {
  const boundary = `----hify-workflow-visible-uat-${Date.now()}-${Math.random().toString(16).slice(2)}`
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

async function findOpenRouterQwenModel(baseUrl) {
  for (let page = 1; page <= 20; page += 1) {
    const providers = await getJson(baseUrl, `/api/v1/providers?page=${page}&pageSize=100`, 'list providers')
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      if (String(provider.baseUrl || '') !== 'https://openrouter.ai/api/v1') continue
      for (const model of provider.models ?? []) {
        if (model.enabled && String(model.modelId || '') === 'qwen/qwen3.5-9b') return model.id
      }
    }
    if ((providers.list ?? []).length === 0 || page * 100 >= providers.total) break
  }
  throw new Error('OpenRouter qwen/qwen3.5-9b model config is required for visible workflow UAT')
}

async function createKnowledgeBase(baseUrl, marker) {
  const kb = await postJson(
    baseUrl,
    '/api/v1/knowledge-bases',
    { name: `In-app workflow visible UAT KB ${marker}`, description: 'visible browser workflow UAT' },
    'create knowledge base',
  )
  const document = await request(
    baseUrl,
    `/api/v1/knowledge-bases/${kb.id}/documents`,
    multipartTextFile(
      `workflow-inapp-visible-${marker}.txt`,
      `Workflow knowledge marker ${marker}. Approved answer is WF_KB_VISIBLE_${marker}.`,
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

async function createPublishedChildWorkflow(baseUrl, stamp) {
  const child = await postJson(baseUrl, '/api/v1/workflows', {
    name: `In-app Workflow Child ${stamp}`,
    description: 'visible workflow execute workflow child',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['ticket'], ui: { position: { x: 120, y: 180 } } } },
      {
        nodeKey: 'format_1',
        type: 'TEXT_PROCESS',
        name: '文本处理',
        config: {
          operation: 'format_template',
          template: 'workflow child handled {{start.ticket}}',
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

async function createWorkflow(baseUrl, name, nodes, edges) {
  return postJson(baseUrl, '/api/v1/workflows', {
    name,
    description: 'visible in-app Browser workflow output UAT',
    nodes,
    edges,
  }, `create ${name}`)
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
    { name: `In-app Workflow Tool MCP ${stamp}`, endpoint: 'mock://tools', description: 'visible workflow UAT tool call' },
    'create mcp server',
  )
  const agentMarker = `WF_AGENT_VISIBLE_${stamp}`
  const agent = await postJson(baseUrl, '/api/v1/agents', {
    name: `In-app Workflow Agent ${stamp}`,
    description: 'visible browser workflow agent call target',
    systemPrompt: `Reply exactly with ${agentMarker}.`,
    modelConfigId,
    temperature: 0,
    maxTokens: 64,
    maxContextTurns: 4,
    toolIds: [],
  }, 'create agent')
  const chainAgentMarker = `WF_AGENT_CHAIN_${stamp}`
  const chainAgent = await postJson(baseUrl, '/api/v1/agents', {
    name: `In-app Workflow Chain Agent ${stamp}`,
    description: 'visible browser workflow strict-chain agent target',
    systemPrompt: 'Return exactly the audit marker requested by the user, with no quotes and no extra text.',
    modelConfigId,
    temperature: 0,
    maxTokens: 160,
    maxContextTurns: 4,
    toolIds: [],
  }, 'create strict-chain agent')

  const cases = []
  const baseStart = { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT', 'userMessage'], ui: { position: { x: 120, y: 180 } } } }

  cases.push({
    key: 'condition_message',
    title: 'CONDITION + MESSAGE + END',
    input: 'vip customer',
    expected: `WF_VIP_VISIBLE_${stamp}`,
    workflow: await createWorkflow(baseUrl, `In-app WF CONDITION ${stamp}`, [
      baseStart,
      {
        nodeKey: 'condition_1',
        type: 'CONDITION',
        name: '条件',
        config: {
          branches: [{ key: 'vip', conditions: [{ left: '{{start.USER_INPUT}}', operator: 'contains', right: 'vip' }] }],
          defaultBranch: 'normal',
          outputVariable: 'route',
          ui: { position: { x: 440, y: 180 } },
        },
      },
      { nodeKey: 'vip_msg', type: 'MESSAGE', name: 'VIP', config: { content: `WF_VIP_VISIBLE_${stamp}`, outputVariable: 'content', ui: { position: { x: 760, y: 100 } } } },
      { nodeKey: 'normal_msg', type: 'MESSAGE', name: 'Normal', config: { content: 'WF_NORMAL_SHOULD_NOT_APPEAR', outputVariable: 'content', ui: { position: { x: 760, y: 300 } } } },
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
    key: 'transform_variables',
    title: 'TEXT_PROCESS + JSON_PARSE + VARIABLE_AGGREGATION + VARIABLE_ASSIGN',
    input: '  Ada  ',
    expected: 'wf route=gold name=Ada',
    workflow: await createWorkflow(baseUrl, `In-app WF TRANSFORM ${stamp}`, [
      baseStart,
      { nodeKey: 'trim_1', type: 'TEXT_PROCESS', name: 'Trim', config: { operation: 'trim', source: '{{start.USER_INPUT}}', outputVariable: 'name', ui: { position: { x: 420, y: 180 } } } },
      {
        nodeKey: 'json_1',
        type: 'JSON_PARSE',
        name: 'JSON',
        config: {
          sourceValue: '{"tier":"gold","name":"{{trim_1.name}}"}',
          outputVariable: 'parsed',
          fieldMap: [{ name: 'tier', path: '$.tier' }, { name: 'name', path: '$.name' }],
          ui: { position: { x: 680, y: 180 } },
        },
      },
      {
        nodeKey: 'aggregate_1',
        type: 'VARIABLE_AGGREGATION',
        name: '聚合',
        config: {
          strategy: 'first_non_empty',
          sources: [{ name: 'primary', value: '{{json_1.tier}}' }, { name: 'fallback', value: '{{start.USER_INPUT}}' }],
          outputVariable: 'selected',
          ui: { position: { x: 940, y: 180 } },
        },
      },
      { nodeKey: 'assign_1', type: 'VARIABLE_ASSIGN', name: '赋值', config: { targetScope: 'flow', targetVariable: 'route', source: '{{aggregate_1.selected}}', writeMode: 'set', ui: { position: { x: 1200, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'wf route={{flow.route}} name={{trim_1.name}}', ui: { position: { x: 1460, y: 180 } } } },
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
    input: `WF_LLM_VISIBLE_${stamp}`,
    expected: `WF_LLM_VISIBLE_${stamp}`,
    workflow: await createWorkflow(baseUrl, `In-app WF LLM ${stamp}`, [
      baseStart,
      { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { modelConfigId, prompt: 'Reply exactly this token and nothing else: {{start.USER_INPUT}}', outputVariable: 'answer', temperature: 0, maxTokens: 64, ui: { position: { x: 480, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{llm_1.answer}}', ui: { position: { x: 840, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
      { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'agent_call_real_qwen',
    title: 'AGENT_CALL real OpenRouter-backed agent',
    input: 'hello workflow agent',
    expected: agentMarker,
    workflow: await createWorkflow(baseUrl, `In-app WF AGENT ${stamp}`, [
      baseStart,
      {
        nodeKey: 'agent_call_1',
        type: 'AGENT_CALL',
        name: '智能体',
        config: {
          targetAgentId: agent.id,
          inputMappings: [{ name: 'message', valueMode: 'reference', value: `Reply exactly with ${agentMarker}. User message: {{start.USER_INPUT}}`, required: true }],
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

  const strictInput = `  WF-CHAIN-${stamp}  `
  const strictName = `WF-CHAIN-${stamp}`
  const strictAggregate = `platinum-go-${strictName}`
  const strictCode = `WFSTEP_${stamp}:${strictName}:${strictAggregate}`
  const strictLlm = `WFLLM_${stamp}__${strictCode}`
  const strictAgent = `${chainAgentMarker}__${strictLlm}`
  const strictChild = `workflow child handled ${strictAgent}`
  cases.push({
    key: 'strict_chain',
    title: 'Strict chain: TEXT + CONDITION + JSON + VARIABLES + CODE + LLM + AGENT + CHILD',
    input: strictInput,
    expected: strictChild,
    strict: {
      stamp,
      strictName,
      strictAggregate,
      strictCode,
      strictLlm,
      strictAgent,
      strictChild,
      modelConfigId,
    },
    workflow: await createWorkflow(baseUrl, `In-app WF STRICT CHAIN ${stamp}`, [
      baseStart,
      { nodeKey: 'trim_1', type: 'TEXT_PROCESS', name: 'Trim', config: { operation: 'trim', source: '{{start.USER_INPUT}}', outputVariable: 'name', ui: { position: { x: 420, y: 180 } } } },
      {
        nodeKey: 'condition_1',
        type: 'CONDITION',
        name: '条件',
        config: {
          branches: [{ key: 'go', conditions: [{ left: '{{trim_1.name}}', operator: 'contains', right: 'WF-CHAIN' }] }],
          defaultBranch: 'stop',
          outputVariable: 'route',
          ui: { position: { x: 700, y: 180 } },
        },
      },
      {
        nodeKey: 'json_1',
        type: 'JSON_PARSE',
        name: 'JSON',
        config: {
          sourceValue: '{"raw":"{{start.USER_INPUT}}","trimmed":"{{trim_1.name}}","route":"{{condition_1.route}}","tier":"platinum"}',
          outputVariable: 'parsed',
          fieldMap: [
            { name: 'raw', path: '$.raw' },
            { name: 'trimmed', path: '$.trimmed' },
            { name: 'route', path: '$.route' },
            { name: 'tier', path: '$.tier' },
          ],
          ui: { position: { x: 980, y: 180 } },
        },
      },
      {
        nodeKey: 'aggregate_1',
        type: 'VARIABLE_AGGREGATION',
        name: '聚合',
        config: {
          strategy: 'concat',
          separator: '-',
          sources: [
            { name: 'jsonTier', value: '{{json_1.tier}}' },
            { name: 'jsonRoute', value: '{{json_1.route}}' },
            { name: 'jsonName', value: '{{json_1.trimmed}}' },
          ],
          outputVariable: 'selected',
          ui: { position: { x: 1260, y: 180 } },
        },
      },
      { nodeKey: 'assign_1', type: 'VARIABLE_ASSIGN', name: '赋值', config: { targetScope: 'flow', targetVariable: 'route', source: '{{aggregate_1.selected}}', writeMode: 'set', outputVariable: 'assignedRoute', ui: { position: { x: 1540, y: 180 } } } },
      {
        nodeKey: 'code_1',
        type: 'CODE',
        name: '代码',
        config: {
          language: 'python',
          code: `def main(args):\n    return {"codeToken": "WFSTEP_${stamp}:" + str(args.get("name", "")) + ":" + str(args.get("route", ""))}`,
          inputParameters: [
            { name: 'name', value: '{{json_1.trimmed}}' },
            { name: 'route', value: '{{flow.route}}' },
            { name: 'branch', value: '{{json_1.route}}' },
          ],
          outputParameters: [{ name: 'codeToken', type: 'string' }],
          ui: { position: { x: 1820, y: 180 } },
        },
      },
      {
        nodeKey: 'llm_1',
        type: 'LLM',
        name: '大模型',
        config: {
          modelConfigId,
          prompt: `Return exactly this audit marker, with no quotes and no extra text: WFLLM_${stamp}__{{code_1.codeToken}}`,
          outputVariable: 'answer',
          temperature: 0,
          maxTokens: 160,
          ui: { position: { x: 2100, y: 180 } },
        },
      },
      {
        nodeKey: 'agent_call_1',
        type: 'AGENT_CALL',
        name: '智能体',
        config: {
          targetAgentId: chainAgent.id,
          inputMappings: [{ name: 'message', valueMode: 'reference', value: `Return exactly this audit marker, with no quotes and no extra text: ${chainAgentMarker}__{{llm_1.answer}}`, required: true }],
          outputMappings: [{ source: 'answer', target: 'agentAnswer' }],
          outputParameters: [{ name: 'agentAnswer', type: 'string' }, { name: 'status', type: 'string' }],
          timeoutMs: 90000,
          maxDepth: 3,
          ui: { position: { x: 2380, y: 180 } },
        },
      },
      {
        nodeKey: 'execute_workflow_1',
        type: 'EXECUTE_WORKFLOW',
        name: '工作流',
        config: {
          targetWorkflowId: child.id,
          inputMappings: [{ name: 'ticket', valueMode: 'reference', value: '{{agent_call_1.agentAnswer}}', required: true }],
          outputMappings: [{ source: 'summary', target: 'childSummary' }],
          outputParameters: [{ name: 'childSummary', type: 'string' }, { name: 'nestedRunId', type: 'number' }, { name: 'status', type: 'string' }],
          maxDepth: 3,
          ui: { position: { x: 2660, y: 180 } },
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: {
          outputVariable: 'final',
          output: `WF_STRICT_FINAL ${stamp} | raw={{json_1.raw}} | name={{json_1.trimmed}} | route={{json_1.route}} | agg={{aggregate_1.selected}} | flow={{flow.route}} | code={{code_1.codeToken}} | llm={{llm_1.answer}} | agent={{agent_call_1.agentAnswer}} | child={{execute_workflow_1.childSummary}}`,
          ui: { position: { x: 2940, y: 180 } },
        },
      },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'trim_1', condition: null },
      { sourceNodeKey: 'trim_1', targetNodeKey: 'condition_1', condition: null },
      { sourceNodeKey: 'condition_1', targetNodeKey: 'json_1', condition: 'go' },
      { sourceNodeKey: 'json_1', targetNodeKey: 'aggregate_1', condition: null },
      { sourceNodeKey: 'aggregate_1', targetNodeKey: 'assign_1', condition: null },
      { sourceNodeKey: 'assign_1', targetNodeKey: 'code_1', condition: null },
      { sourceNodeKey: 'code_1', targetNodeKey: 'llm_1', condition: null },
      { sourceNodeKey: 'llm_1', targetNodeKey: 'agent_call_1', condition: null },
      { sourceNodeKey: 'agent_call_1', targetNodeKey: 'execute_workflow_1', condition: null },
      { sourceNodeKey: 'execute_workflow_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'knowledge',
    title: 'KNOWLEDGE + END',
    input: `Workflow knowledge marker ${stamp}`,
    expected: `WF_KB_VISIBLE_${stamp}`,
    workflow: await createWorkflow(baseUrl, `In-app WF KNOWLEDGE ${stamp}`, [
      baseStart,
      { nodeKey: 'knowledge_1', type: 'KNOWLEDGE', name: '知识库', config: { query: '{{start.USER_INPUT}}', knowledgeBaseId: kb.id, topK: 2, outputVariable: 'answer', ui: { position: { x: 480, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'WF KB {{knowledge_1.answer}}', ui: { position: { x: 840, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'knowledge_1', condition: null },
      { sourceNodeKey: 'knowledge_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'api_call',
    title: 'API_CALL + END',
    input: `WF-API-${stamp}`,
    expected: `API_REAL: POST /echo/WF-API-${stamp}`,
    workflow: await createWorkflow(baseUrl, `In-app WF API ${stamp}`, [
      baseStart,
      { nodeKey: 'api_1', type: 'API_CALL', name: 'API 调用', config: { method: 'POST', endpoint: `${apiServer.url}/echo/{{start.USER_INPUT}}`, outputVariable: 'response', ui: { position: { x: 500, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{api_1.response}}', ui: { position: { x: 860, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'api_1', condition: null },
      { sourceNodeKey: 'api_1', targetNodeKey: 'end', condition: null },
    ]),
  })

  cases.push({
    key: 'tool_call',
    title: 'TOOL_CALL mock MCP',
    input: 'A-300',
    expected: 'Order A-300 status: SHIPPED',
    workflow: await createWorkflow(baseUrl, `In-app WF TOOL ${stamp}`, [
      baseStart,
      {
        nodeKey: 'tool_call_1',
        type: 'TOOL_CALL',
        name: '工具调用',
        config: { resourceType: 'MCP_TOOL', resourceId: `mcp:${mcp.id}:lookup_order`, serverIds: [mcp.id], toolName: 'lookup_order', inputMappings: [{ name: 'orderId', valueMode: 'reference', value: '{{start.USER_INPUT}}', required: true }], outputParameters: [{ name: 'result', type: 'string' }], ui: { position: { x: 500, y: 180 } } },
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
    input: 'WF-C-453',
    expected: 'workflow child handled WF-C-453',
    workflow: await createWorkflow(baseUrl, `In-app WF EXECUTE ${stamp}`, [
      baseStart,
      {
        nodeKey: 'execute_workflow_1',
        type: 'EXECUTE_WORKFLOW',
        name: '工作流',
        config: { targetWorkflowId: child.id, inputMappings: [{ name: 'ticket', valueMode: 'reference', value: '{{start.USER_INPUT}}', required: true }], outputMappings: [{ source: 'summary', target: 'childSummary' }], maxDepth: 3, outputParameters: [{ name: 'childSummary', type: 'string' }, { name: 'nestedRunId', type: 'number' }, { name: 'status', type: 'string' }], ui: { position: { x: 500, y: 180 } } },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{execute_workflow_1.childSummary}}', ui: { position: { x: 880, y: 180 } } } },
    ], [
      { sourceNodeKey: 'start', targetNodeKey: 'execute_workflow_1', condition: null },
      { sourceNodeKey: 'execute_workflow_1', targetNodeKey: 'end', condition: null },
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

async function uniqueVisibleRunButton(page) {
  const locator = page.getByRole('button', { name: '试运行', exact: true })
  const count = await locator.count()
  for (let index = count - 1; index >= 0; index -= 1) {
    const button = locator.nth(index)
    if (await button.isVisible().catch(() => false)) return button
  }
  throw new Error('workflow run button not visible')
}

async function waitForWorkflowOutput(page, expected, timeoutMs = 120000) {
  const deadline = Date.now() + timeoutMs
  let latest = ''
  while (Date.now() < deadline) {
    latest = await page.evaluate(() => document.querySelector('[data-testid="test-run-panel"]')?.textContent || '')
    if (latest.includes(expected)) return latest
    if (latest.includes('暂无回复内容')) throw new Error(`Unexpected empty reply placeholder while waiting for ${expected}: ${latest}`)
    await page.waitForTimeout(500)
  }
  throw new Error(`Timed out waiting for workflow output ${expected}; latest=${latest}`)
}

function runIdFromText(text, label) {
  const match = String(text || '').match(/Run #(\d+)/)
  assert(match, `${label} output should expose runtime run id, got: ${text}`)
  return Number(match[1])
}

function requireNode(nodes, nodeKey, nodeType) {
  const node = nodes.find((item) => item.nodeKey === nodeKey && (!nodeType || item.nodeType === nodeType))
  assert(node, `Expected runtime node ${nodeKey}${nodeType ? `/${nodeType}` : ''}: ${JSON.stringify(nodes)}`)
  assert(node.status === 'COMPLETED', `Expected ${nodeKey} to complete, got ${JSON.stringify(node)}`)
  assert(!node.error, `Expected ${nodeKey} without error, got ${JSON.stringify(node)}`)
  return node
}

function assertStrictWorkflowDefinitions(cases) {
  const strictCase = cases.find((testCase) => testCase.key === 'strict_chain')
  assert(strictCase, 'strict workflow UAT case is required')
  const byKey = Object.fromEntries(strictCase.workflow.nodes.map((node) => [node.nodeKey, node]))
  const json = byKey.json_1?.config || {}
  assert(String(json.sourceValue || '').includes('{{start.USER_INPUT}}'), 'JSON_PARSE source must reference start.USER_INPUT')
  assert(String(json.sourceValue || '').includes('{{trim_1.name}}'), 'JSON_PARSE source must reference TEXT_PROCESS output')
  assert(String(json.sourceValue || '').includes('{{condition_1.route}}'), 'JSON_PARSE source must reference CONDITION output')
  assert((json.fieldMap || []).every((field) => field.name && field.path), 'JSON_PARSE fieldMap names and paths must be non-empty')
  const aggregateSources = byKey.aggregate_1?.config?.sources || []
  assert(aggregateSources.length >= 3 && aggregateSources.every((source) => String(source.value || '').startsWith('{{json_1.')), 'VARIABLE_AGGREGATION must use JSON_PARSE outputs')
  const assign = byKey.assign_1?.config || {}
  assert(assign.targetVariable && assign.source === '{{aggregate_1.selected}}', 'VARIABLE_ASSIGN target/source must be explicit and upstream-referenced')
  const codeInputs = byKey.code_1?.config?.inputParameters || []
  assert(codeInputs.some((input) => input.value === '{{json_1.trimmed}}'), 'CODE must reference JSON parsed name')
  assert(codeInputs.some((input) => input.value === '{{flow.route}}'), 'CODE must reference assigned flow variable')
  assert(String(byKey.llm_1?.config?.prompt || '').includes('{{code_1.codeToken}}'), 'LLM prompt must reference CODE output')
  const agentInputs = byKey.agent_call_1?.config?.inputMappings || []
  assert(agentInputs.some((input) => input.valueMode === 'reference' && String(input.value || '').includes('{{llm_1.answer}}')), 'AGENT must reference LLM output')
  const executeInputs = byKey.execute_workflow_1?.config?.inputMappings || []
  assert(executeInputs.some((input) => input.valueMode === 'reference' && input.value === '{{agent_call_1.agentAnswer}}'), 'EXECUTE_WORKFLOW must reference AGENT output')
  const endOutput = String(byKey.end?.config?.output || '')
  for (const requiredRef of ['{{json_1.raw}}', '{{aggregate_1.selected}}', '{{flow.route}}', '{{code_1.codeToken}}', '{{llm_1.answer}}', '{{agent_call_1.agentAnswer}}', '{{execute_workflow_1.childSummary}}']) {
    assert(endOutput.includes(requiredRef), `END output missing ${requiredRef}`)
  }
}

async function assertWorkflowStrictRuntimeNodes(baseUrl, runId, testCase) {
  if (!testCase.strict) return null
  const nodePage = await getJson(baseUrl, `/api/v1/runtime-runs/${runId}/nodes`, `${testCase.key} runtime nodes`)
  const nodes = nodePage.list || []
  const strict = testCase.strict
  assert(nodes.length >= 10, `Strict workflow should record all runtime nodes, got ${nodes.length}`)
  const json = requireNode(nodes, 'json_1', 'JSON_PARSE')
  assert(json.outputs?.raw === testCase.input, `JSON raw should keep original input, got ${JSON.stringify(json.outputs)}`)
  assert(json.outputs?.trimmed === strict.strictName, `JSON trimmed should come from TEXT_PROCESS, got ${JSON.stringify(json.outputs)}`)
  assert(json.outputs?.route === 'go', `JSON route should come from CONDITION, got ${JSON.stringify(json.outputs)}`)
  assert(json.outputs?.parseStatus === 'SUCCEEDED', `JSON parse should succeed, got ${JSON.stringify(json.outputs)}`)
  const aggregate = requireNode(nodes, 'aggregate_1', 'VARIABLE_AGGREGATION')
  assert(aggregate.outputs?.selected === strict.strictAggregate, `Aggregate should concatenate JSON outputs, got ${JSON.stringify(aggregate.outputs)}`)
  assert((aggregate.outputs?.sourceStatus || []).every((source) => source.name && source.empty === false), `Aggregate sources must be non-empty, got ${JSON.stringify(aggregate.outputs)}`)
  const assign = requireNode(nodes, 'assign_1', 'VARIABLE_ASSIGN')
  assert(assign.outputs?.variable === 'route' && assign.outputs?.assigned === true, `Assign should write non-empty flow.route, got ${JSON.stringify(assign.outputs)}`)
  assert(assign.outputs?.value === strict.strictAggregate, `Assign value should match aggregate, got ${JSON.stringify(assign.outputs)}`)
  const code = requireNode(nodes, 'code_1', 'CODE')
  assert(code.outputs?.codeToken === strict.strictCode, `CODE output should include upstream JSON/flow variables, got ${JSON.stringify(code.outputs)}`)
  const llm = requireNode(nodes, 'llm_1', 'LLM')
  assert(llm.outputs?.answer === strict.strictLlm, `LLM output should echo strict marker, got ${JSON.stringify(llm.outputs)}`)
  assert(String(llm.outputs?.__debug?.llm?.input?.model || '').includes('qwen/qwen3.5-9b'), `LLM must use qwen/qwen3.5-9b, got ${JSON.stringify(llm.outputs?.__debug)}`)
  assert(Number(llm.outputs?.__usage?.totalTokens || 0) > 0, `LLM must record real provider usage, got ${JSON.stringify(llm.outputs)}`)
  assert(!String(llm.outputs?.answer || '').includes('LLM mock:'), `LLM must not use mock output, got ${JSON.stringify(llm.outputs)}`)
  const agent = requireNode(nodes, 'agent_call_1', 'AGENT_CALL')
  assert(agent.outputs?.agentAnswer === strict.strictAgent, `AGENT must use LLM output, got ${JSON.stringify(agent.outputs)}`)
  const child = requireNode(nodes, 'execute_workflow_1', 'EXECUTE_WORKFLOW')
  assert(child.outputs?.childSummary === strict.strictChild, `Child workflow must use AGENT output, got ${JSON.stringify(child.outputs)}`)
  const end = requireNode(nodes, 'end', 'END')
  const final = String(end.outputs?.final || '')
  for (const expected of [strict.strictName, strict.strictAggregate, strict.strictCode, strict.strictLlm, strict.strictAgent, strict.strictChild]) {
    assert(final.includes(expected), `END final missing ${expected}: ${final}`)
  }
  assert(!final.includes('暂无回复内容'), `END final must not include empty placeholder: ${final}`)
  return { nodes, final }
}

async function screenshot(tab, path) {
  const bytes = await tab.screenshot({ fullPage: true })
  await writeFile(path, bytes)
}

async function runWorkflowInVisibleUi(tab, baseUrl, testCase, index, outputDir) {
  await tab.goto(`${baseUrl}/workflows/${testCase.workflow.id}/canvas`)
  await tab.playwright.waitForLoadState({ state: 'load', timeoutMs: 30000 }).catch(() => undefined)
  await tab.playwright.getByText(testCase.workflow.name, { exact: false }).waitFor({ state: 'visible', timeoutMs: 30000 })
  const runButton = await uniqueVisibleRunButton(tab.playwright)
  await runButton.click({ force: true, timeoutMs: 5000 })
  const panel = tab.playwright.getByTestId('test-run-panel')
  await panel.waitFor({ state: 'visible', timeoutMs: 15000 })
  await panel.getByPlaceholder('输入 userMessage').fill(testCase.input, { timeoutMs: 5000 })
  await panel.getByRole('button', { name: '运行', exact: true }).click({ force: true, timeoutMs: 5000 })
  const outputPreview = await waitForWorkflowOutput(tab.playwright, testCase.expected)
  const runId = runIdFromText(outputPreview, testCase.key)
  const runtime = await assertWorkflowStrictRuntimeNodes(baseUrl, runId, testCase)
  const path = `${outputDir}/inapp-workflow-visible-uat-${String(index + 1).padStart(2, '0')}-${testCase.key}.png`
  await screenshot(tab, path)
  return {
    key: testCase.key,
    title: testCase.title,
    workflowId: testCase.workflow.id,
    runId,
    expected: testCase.expected,
    passed: true,
    screenshot: path,
    outputPreview: outputPreview.slice(0, 500),
    runtimeNodeCount: runtime?.nodes?.length || null,
    finalOutput: runtime?.final || null,
  }
}

export async function runInAppWorkflowVisibleOutputUat(options = {}) {
  const browser = options.browser || globalThis.browser
  assert(browser, 'in-app Browser is required')
  const baseUrl = options.baseUrl || defaultBaseUrl
  const outputDir = options.outputDir || '/Users/vincento/work/develop/hify/output/playwright'
  await mkdir(outputDir, { recursive: true })
  const tab = options.tab || await ensureVisibleBrowser(browser)
  globalThis.tab = tab
  const fixtures = await createFixtures(baseUrl)
  assertStrictWorkflowDefinitions(fixtures.cases)
  const results = []
  try {
    const selectedCases = fixtures.cases
      .map((testCase, index) => ({ testCase, index }))
      .filter(({ testCase }) => !Array.isArray(options.onlyKeys) || options.onlyKeys.includes(testCase.key))
    for (const { testCase, index } of selectedCases) {
      results.push(await runWorkflowInVisibleUi(tab, baseUrl, testCase, index, outputDir))
    }
  } finally {
    await fixtures.apiServer.close()
  }
  const summaryPath = `${outputDir}/inapp-workflow-visible-uat-summary-${fixtures.stamp}.json`
  await writeFile(summaryPath, JSON.stringify({ stamp: fixtures.stamp, results }, null, 2))
  return { stamp: fixtures.stamp, summaryPath, total: results.length, passed: results.length, results }
}
