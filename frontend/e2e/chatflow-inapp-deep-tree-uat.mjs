import { mkdir, writeFile } from 'node:fs/promises'

const defaultBaseUrl = 'http://127.0.0.1:5173'
const requiredTypes = [
  'LLM',
  'AGENT_CALL',
  'EXECUTE_WORKFLOW',
  'QUESTION',
  'INTENT_RECOGNITION',
  'JSON_PARSE',
  'HUMAN_INPUT',
  'VARIABLE_ASSIGN',
  'VARIABLE_AGGREGATION',
  'CONDITION',
  'CODE',
]

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
  throw new Error('OpenRouter qwen/qwen3.5-9b model config is required for deep chatflow UAT')
}

async function createPublishedChildWorkflow(baseUrl, stamp) {
  const child = await postJson(baseUrl, '/api/v1/workflows', {
    name: `In-app Deep Child ${stamp}`,
    description: 'Deep visible Browser UAT child workflow',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['ticket'], ui: { position: { x: 120, y: 160 } } } },
      {
        nodeKey: 'format_1',
        type: 'TEXT_PROCESS',
        name: '子流程格式化',
        config: {
          operation: 'format_template',
          template: 'CHILD_DEEP handled {{start.ticket}}',
          outputParameters: [{ name: 'summary', type: 'string' }],
          ui: { position: { x: 500, y: 160 } },
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'summary', output: '{{format_1.summary}}', ui: { position: { x: 880, y: 160 } } } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'format_1', condition: null },
      { sourceNodeKey: 'format_1', targetNodeKey: 'end', condition: null },
    ],
  }, 'create deep child workflow')
  return putJson(baseUrl, `/api/v1/workflows/${child.id}`, {
    name: child.name,
    description: child.description,
    status: 'PUBLISHED',
    nodes: child.nodes,
    edges: child.edges,
  }, 'publish deep child workflow')
}

function chatflowPayload(name, nodes, edges) {
  return { name, description: 'visible in-app Browser deep tree UAT', nodes, edges }
}

async function createChatflow(baseUrl, name, nodes, edges) {
  return postJson(baseUrl, '/api/v1/chatflows', chatflowPayload(name, nodes, edges), `create ${name}`)
}

async function createAgent(baseUrl, modelConfigId, stamp, caseId, agentToken) {
  return postJson(baseUrl, '/api/v1/agents', {
    name: `Deep Tree Agent ${caseId} ${stamp}`,
    description: 'Deep visible Browser UAT agent target',
    systemPrompt: `Return exactly this audit marker prefix followed by the user's message, with no quotes and no extra text: ${agentToken}__`,
    modelConfigId,
    temperature: 0,
    maxTokens: 160,
    maxContextTurns: 2,
    toolIds: [],
  }, `create deep agent ${caseId}`)
}

function node(nodeKey, type, name, config, x, y) {
  return { nodeKey, type, name, config: { ...config, ui: { position: { x, y } } } }
}

function buildDeepTreeGraph({ caseId, childWorkflowId, agentId, modelConfigId, tokens, expected }) {
  const questionPromptTemplate = '问题节点确认 {{execute_workflow_1.childSummary}}'
  const humanPromptTemplate = '人工输入确认 {{question_1.answer}}'
  const nodes = [
    node('start', 'START', '开始', { outputVariables: ['sys.query'] }, 80, 260),
    node('intent_1', 'INTENT_RECOGNITION', '意图识别', {
      inputSource: '{{start.sys.query}}',
      outputVariable: 'intent',
      classifierMode: 'fake',
      defaultIntent: 'fallback',
      intents: [
        { key: 'deep', name: '深度测试', description: '深度流程树 UAT', examples: ['deep', caseId] },
        { key: 'other', name: '其他', description: '非本次路径', examples: ['other'] },
      ],
    }, 360, 260),
    node('selector_1', 'CONDITION', '选择器', {
      conditionBranches: [{ key: 'go', conditions: [{ left: '{{intent_1.intent}}', operator: 'equals', right: 'deep' }] }],
      defaultBranch: 'fallback',
      outputVariable: 'route',
    }, 650, 260),
    node('intent_fallback', 'MESSAGE', '意图未命中', { content: `INTENT_FALLBACK_SHOULD_NOT_APPEAR_${caseId}`, outputVariable: 'content' }, 650, 60),
    node('selector_fallback', 'MESSAGE', '选择器未命中', { content: `SELECTOR_FALLBACK_SHOULD_NOT_APPEAR_${caseId}`, outputVariable: 'content' }, 940, 60),
    node('json_1', 'JSON_PARSE', 'JSON解析', {
      sourceValue: JSON.stringify({
        caseId: '{{start.sys.query}}',
        intent: '{{intent_1.intent}}',
        route: '{{selector_1.route}}',
        tier: tokens.tier,
        priority: tokens.priority,
      }),
      outputVariable: 'parsed',
      fieldMap: [
        { name: 'caseId', path: '$.caseId' },
        { name: 'intent', path: '$.intent' },
        { name: 'route', path: '$.route' },
        { name: 'tier', path: '$.tier' },
        { name: 'priority', path: '$.priority' },
      ],
    }, 940, 260),
    node('aggregate_1', 'VARIABLE_AGGREGATION', '变量聚合', {
      strategy: 'concat',
      separator: '-',
      sources: [
        { name: 'jsonTier', value: '{{json_1.tier}}' },
        { name: 'jsonRoute', value: '{{json_1.route}}' },
        { name: 'jsonIntent', value: '{{json_1.intent}}' },
      ],
      outputVariable: 'selected',
    }, 1220, 260),
    node('assign_1', 'VARIABLE_ASSIGN', '变量赋值', {
      targetScope: 'flow',
      targetVariable: 'route',
      source: '{{aggregate_1.selected}}',
      writeMode: 'set',
      outputVariable: 'assignedRoute',
    }, 1500, 260),
    node('code_1', 'CODE', '代码', {
      language: 'python',
      code: `def main(args):\n    return {"codeToken": "${tokens.code}:" + str(args.get("caseId", "")) + ":" + str(args.get("route", ""))}`,
      inputParameters: [
        { name: 'caseId', value: '{{json_1.caseId}}' },
        { name: 'route', value: '{{flow.route}}' },
        { name: 'selectorRoute', value: '{{selector_1.route}}' },
      ],
      outputParameters: [{ name: 'codeToken', type: 'string' }],
    }, 1780, 260),
    node('llm_1', 'LLM', 'LLM', {
      modelConfigId,
      prompt: `Return exactly this audit marker, with no quotes and no extra text: ${tokens.llm}__{{code_1.codeToken}}`,
      outputVariable: 'answer',
      temperature: 0,
      maxTokens: 160,
    }, 2060, 260),
    node('agent_call_1', 'AGENT_CALL', 'AGENT', {
      targetAgentId: agentId,
      inputMappings: [{ name: 'message', valueMode: 'reference', value: '{{llm_1.answer}}', required: true }],
      outputMappings: [{ source: 'answer', target: 'agentAnswer' }],
      outputParameters: [
        { name: 'agentAnswer', type: 'string' },
        { name: 'status', type: 'string' },
      ],
      timeoutMs: 90000,
      maxDepth: 3,
    }, 2340, 260),
    node('execute_workflow_1', 'EXECUTE_WORKFLOW', '工作流', {
      targetWorkflowId: childWorkflowId,
      inputMappings: [{ name: 'ticket', valueMode: 'reference', value: '{{agent_call_1.agentAnswer}}', required: true }],
      outputMappings: [{ source: 'summary', target: 'childSummary' }],
      outputParameters: [
        { name: 'childSummary', type: 'string' },
        { name: 'nestedRunId', type: 'number' },
        { name: 'status', type: 'string' },
      ],
      maxDepth: 3,
    }, 2620, 260),
    node('question_1', 'QUESTION', '问题', {
      question: questionPromptTemplate,
      outputVariable: 'answer',
      answerType: 'text',
    }, 2900, 260),
    node('human_input_1', 'HUMAN_INPUT', '人工输入', {
      prompt: humanPromptTemplate,
      approvalMode: 'input',
      outputVariable: 'payload',
    }, 3180, 260),
    node('end', 'END', '结束', {
      outputVariable: 'final',
      output: [
        `FINAL_DEEP ${caseId}`,
        'intent={{intent_1.intent}}',
        'selector={{selector_1.route}}',
        'json={{json_1.caseId}}',
        'jsonIntent={{json_1.intent}}',
        'jsonRoute={{json_1.route}}',
        'agg={{aggregate_1.selected}}',
        'route={{flow.route}}',
        'code={{code_1.codeToken}}',
        'llm={{llm_1.answer}}',
        'agent={{agent_call_1.agentAnswer}}',
        'child={{execute_workflow_1.childSummary}}',
        'question={{question_1.answer}}',
        'human={{human_input_1.payload}}',
      ].join(' | '),
    }, 3460, 260),
  ]

  const edges = [
    { sourceNodeKey: 'start', targetNodeKey: 'intent_1', condition: null },
    { sourceNodeKey: 'intent_1', targetNodeKey: 'selector_1', condition: 'deep' },
    { sourceNodeKey: 'intent_1', targetNodeKey: 'intent_fallback', condition: null },
    { sourceNodeKey: 'selector_1', targetNodeKey: 'json_1', condition: 'go' },
    { sourceNodeKey: 'selector_1', targetNodeKey: 'selector_fallback', condition: null },
    { sourceNodeKey: 'intent_fallback', targetNodeKey: 'end', condition: null },
    { sourceNodeKey: 'selector_fallback', targetNodeKey: 'end', condition: null },
    { sourceNodeKey: 'json_1', targetNodeKey: 'aggregate_1', condition: null },
    { sourceNodeKey: 'aggregate_1', targetNodeKey: 'assign_1', condition: null },
    { sourceNodeKey: 'assign_1', targetNodeKey: 'code_1', condition: null },
    { sourceNodeKey: 'code_1', targetNodeKey: 'llm_1', condition: null },
    { sourceNodeKey: 'llm_1', targetNodeKey: 'agent_call_1', condition: null },
    { sourceNodeKey: 'agent_call_1', targetNodeKey: 'execute_workflow_1', condition: null },
    { sourceNodeKey: 'execute_workflow_1', targetNodeKey: 'question_1', condition: null },
    { sourceNodeKey: 'question_1', targetNodeKey: 'human_input_1', condition: null },
    { sourceNodeKey: 'human_input_1', targetNodeKey: 'end', condition: null },
  ]
  const graph = {
    nodes,
    edges,
    questionPrompt: `问题节点确认 ${expected.childSummary}`,
    humanPromptTemplate,
  }
  assertStrictUpstreamReferences(graph)
  return graph
}

function nodeByKey(graph, key) {
  const found = graph.nodes.find((item) => item.nodeKey === key)
  assert(found, `Missing node ${key}`)
  return found
}

function assertNonEmptyString(value, label) {
  assert(typeof value === 'string' && value.trim() !== '', `${label} must be a non-empty string`)
}

function assertIncludes(value, needle, label) {
  assertNonEmptyString(value, label)
  assert(value.includes(needle), `${label} must include ${needle}; got ${value}`)
}

function assertStrictUpstreamReferences(graph) {
  const json = nodeByKey(graph, 'json_1').config
  assertIncludes(json.sourceValue, '{{start.sys.query}}', 'JSON_PARSE sourceValue')
  assertIncludes(json.sourceValue, '{{intent_1.intent}}', 'JSON_PARSE sourceValue')
  assertIncludes(json.sourceValue, '{{selector_1.route}}', 'JSON_PARSE sourceValue')
  for (const field of json.fieldMap || []) {
    assertNonEmptyString(field.name, 'JSON_PARSE fieldMap name')
    assertNonEmptyString(field.path, `JSON_PARSE fieldMap path ${field.name}`)
  }

  const aggregate = nodeByKey(graph, 'aggregate_1').config
  assert((aggregate.sources || []).length >= 3, 'VARIABLE_AGGREGATION must combine at least three upstream sources')
  for (const source of aggregate.sources || []) {
    assertNonEmptyString(source.name, 'VARIABLE_AGGREGATION source name')
    assertIncludes(source.value, '{{', `VARIABLE_AGGREGATION source ${source.name}`)
  }

  const assign = nodeByKey(graph, 'assign_1').config
  assertNonEmptyString(assign.targetVariable, 'VARIABLE_ASSIGN targetVariable')
  assertIncludes(assign.source, '{{aggregate_1.selected}}', 'VARIABLE_ASSIGN source')

  const code = nodeByKey(graph, 'code_1').config
  for (const parameter of code.inputParameters || []) {
    assertNonEmptyString(parameter.name, 'CODE input parameter name')
    assertIncludes(parameter.value, '{{', `CODE input parameter ${parameter.name}`)
  }
  assertIncludes(JSON.stringify(code.inputParameters), '{{json_1.caseId}}', 'CODE inputParameters')
  assertIncludes(JSON.stringify(code.inputParameters), '{{flow.route}}', 'CODE inputParameters')

  const llm = nodeByKey(graph, 'llm_1').config
  assertIncludes(llm.prompt, '{{code_1.codeToken}}', 'LLM prompt')

  const agent = nodeByKey(graph, 'agent_call_1').config
  assert(agent.inputMappings?.[0]?.valueMode === 'reference', 'AGENT_CALL message mapping must use reference mode')
  assert(agent.inputMappings?.[0]?.value === '{{llm_1.answer}}', 'AGENT_CALL message must reference LLM output')

  const child = nodeByKey(graph, 'execute_workflow_1').config
  assert(child.inputMappings?.[0]?.valueMode === 'reference', 'EXECUTE_WORKFLOW input must use reference mode')
  assert(child.inputMappings?.[0]?.value === '{{agent_call_1.agentAnswer}}', 'EXECUTE_WORKFLOW input must reference AGENT output')

  assertIncludes(nodeByKey(graph, 'question_1').config.question, '{{execute_workflow_1.childSummary}}', 'QUESTION prompt')
  assertIncludes(nodeByKey(graph, 'human_input_1').config.prompt, '{{question_1.answer}}', 'HUMAN_INPUT prompt')
  assertIncludes(nodeByKey(graph, 'end').config.output, '{{agent_call_1.agentAnswer}}', 'END output')
}

async function createFixtures(baseUrl) {
  const stamp = Date.now()
  const modelConfigId = await findOpenRouterQwenModel(baseUrl)
  const child = await createPublishedChildWorkflow(baseUrl, stamp)
  const cases = []
  for (let index = 1; index <= 10; index += 1) {
    const caseId = `DEEP_${String(index).padStart(2, '0')}_${stamp}`
    const tokens = {
      tier: index % 2 === 0 ? 'platinum' : 'gold',
      priority: `P${index}`,
      code: `STEP_DEEP_${String(index).padStart(2, '0')}`,
      llm: `LLMMARK_DEEP_${String(index).padStart(2, '0')}_${stamp}`,
      agent: `AGENTMARK_DEEP_${String(index).padStart(2, '0')}_${stamp}`,
    }
    const caseInput = `deep-${caseId}`
    const expected = {
      aggregate: `${tokens.tier}-go-deep`,
      codeToken: '',
      llmAnswer: '',
      agentAnswer: '',
      childSummary: '',
    }
    expected.codeToken = `${tokens.code}:${caseInput}:${expected.aggregate}`
    expected.llmAnswer = `${tokens.llm}__${expected.codeToken}`
    expected.agentAnswer = `${tokens.agent}__${expected.llmAnswer}`
    expected.childSummary = `CHILD_DEEP handled ${expected.agentAnswer}`
    const agent = await createAgent(baseUrl, modelConfigId, stamp, caseId, tokens.agent)
    const graph = buildDeepTreeGraph({
      caseId,
      childWorkflowId: child.id,
      agentId: agent.id,
      modelConfigId,
      tokens,
      expected,
    })
    const chatflow = await createChatflow(baseUrl, `In-app Deep Tree ${String(index).padStart(2, '0')} ${stamp}`, graph.nodes, graph.edges)
    const questionAnswer = `QANS_${caseId}`
    const humanAnswer = `HUMAN_${caseId}`
    cases.push({
      key: `deep_${String(index).padStart(2, '0')}`,
      title: `Deep tree ${index}`,
      message: caseInput,
      questionAnswer,
      humanAnswer,
      graph,
      tokens,
      expected,
      chatflow,
      expectedHumanPrompt: `人工输入确认 ${questionAnswer}`,
      expectedFragments: [
        `FINAL_DEEP ${caseId}`,
        'intent=deep',
        'selector=go',
        `json=${caseInput}`,
        'jsonIntent=deep',
        'jsonRoute=go',
        `agg=${expected.aggregate}`,
        `route=${expected.aggregate}`,
        `code=${expected.codeToken}`,
        `llm=${expected.llmAnswer}`,
        `agent=${expected.agentAnswer}`,
        `child=${expected.childSummary}`,
        `question=${questionAnswer}`,
        `human=${humanAnswer}`,
      ],
    })
  }
  return { stamp, cases, childWorkflowId: child.id }
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

async function firstVisible(locator, label) {
  const count = await locator.count()
  for (let index = 0; index < count; index += 1) {
    const candidate = locator.nth(index)
    if (await candidate.isVisible().catch(() => false)) return candidate
  }
  throw new Error(`${label} expected at least one visible element, got ${count}`)
}

async function visibleRunButton(scope, label) {
  const candidates = []
  for (const name of ['对话试运行', '试运行']) {
    const locator = scope.getByRole('button', { name, exact: true })
    const count = await locator.count()
    for (let index = 0; index < count; index += 1) {
      const candidate = locator.nth(index)
      if (await candidate.isVisible().catch(() => false)) candidates.push({ name, candidate })
    }
  }
  const run = [...candidates].reverse().find((item) => item.name === '试运行') || candidates[0]
  assert(run, `${label} expected a visible run button`)
  return run.candidate
}

async function readUiState(tab) {
  return tab.playwright.evaluate(() => ({
    messages: Array.from(document.querySelectorAll('[data-testid="chatflow-assistant-message"]')).map((item) => item.textContent || ''),
    resume: Array.from(document.querySelectorAll('[data-testid="chatflow-run-resume-card"] *')).map((item) => item.textContent || item.getAttribute('placeholder') || '').join('\n'),
    status: Array.from(document.querySelectorAll('[data-testid="test-run-panel"] *')).map((item) => item.textContent || '').join('\n'),
    dock: Array.from(document.querySelectorAll('[data-testid="workflow-debug-dock"] *')).map((item) => item.textContent || '').join('\n'),
  }), undefined, { timeoutMs: 5000 })
}

function uiHaystack(state, source = 'any') {
  return [
    source === 'messages' || source === 'any' ? state.messages.join('\n') : '',
    source === 'resume' || source === 'any' ? state.resume : '',
    source === 'status' || source === 'any' ? state.status : '',
    source === 'dock' || source === 'any' ? state.dock : '',
  ].join('\n')
}

async function waitForVisibleText(tab, expected, options = {}) {
  const timeoutMs = options.timeoutMs || 120000
  const deadline = Date.now() + timeoutMs
  let latest = null
  while (Date.now() < deadline) {
    latest = await readUiState(tab)
    const haystack = uiHaystack(latest, options.source || 'any')
    if (haystack.includes(expected)) return { latest, haystack }
    if (haystack.includes('暂无回复内容')) {
      throw new Error(`Unexpected empty reply placeholder while waiting for ${expected}: ${haystack.slice(0, 1000)}`)
    }
    await tab.playwright.waitForTimeout(500)
  }
  throw new Error(`Timed out waiting for visible text ${expected}; latest=${JSON.stringify(latest)}`)
}

async function screenshot(tab, path) {
  const bytes = await tab.screenshot({ fullPage: true })
  await writeFile(path, bytes)
}

function runIdFromText(text, label) {
  const patterns = [/Run #(\d+)/, /runId["':\s]+(\d+)/i, /运行\s*#?(\d+)/]
  for (const pattern of patterns) {
    const match = text.match(pattern)
    if (match) return Number(match[1])
  }
  throw new Error(`${label} could not find runtime run id in visible UI`)
}

async function fillResumeCard(tab, value, label) {
  const panel = await unique(tab.playwright.getByTestId('test-run-panel'), `${label} test panel`)
  const card = await unique(panel.getByTestId('chatflow-run-resume-card'), `${label} resume card`)
  await card.waitFor({ state: 'visible', timeoutMs: 30000 })
  const input = await firstVisible(card.locator('input, textarea'), `${label} resume input`)
  await input.fill(value, { timeoutMs: 5000 })
  const submit = await unique(card.getByRole('button', { name: '提交回复继续', exact: true }), `${label} resume submit`)
  await submit.click({ force: true, timeoutMs: 5000 })
}

async function assertRuntimeNodes(baseUrl, runId, testCase) {
  const result = await getJson(baseUrl, `/api/v1/runtime-runs/${runId}`, `${testCase.key} runtime result`)
  assert(String(result.status || '').toUpperCase() === 'SUCCEEDED', `${testCase.key} runtime status ${result.status}: ${result.error || ''}`)
  const outputText = JSON.stringify(result.output || {})
  for (const fragment of testCase.expectedFragments) {
    assert(outputText.includes(fragment), `${testCase.key} backend result missing ${fragment}: ${outputText}`)
  }

  const nodePage = await getJson(baseUrl, `/api/v1/runtime-runs/${runId}/nodes`, `${testCase.key} runtime nodes`)
  const nodes = nodePage.list || []
  const byType = new Map()
  for (const item of nodes) {
    byType.set(String(item.nodeType), [...(byType.get(String(item.nodeType)) || []), item])
  }
  for (const type of requiredTypes) {
    assert(byType.has(type), `${testCase.key} missing runtime node type ${type}`)
  }
  for (const type of requiredTypes) {
    const completed = (byType.get(type) || []).some((item) => String(item.status || '').toUpperCase() === 'COMPLETED')
    assert(completed, `${testCase.key} node type ${type} did not complete: ${JSON.stringify(byType.get(type) || [])}`)
  }
  const completedNode = (key) => nodes.find((item) => item.nodeKey === key && String(item.status || '').toUpperCase() === 'COMPLETED')
  const json = completedNode('json_1')
  assert(json?.outputs?.caseId === testCase.message, `${testCase.key} JSON_PARSE caseId did not come from start query`)
  assert(json?.outputs?.intent === 'deep', `${testCase.key} JSON_PARSE intent did not come from INTENT_RECOGNITION`)
  assert(json?.outputs?.route === 'go', `${testCase.key} JSON_PARSE route did not come from selector`)
  assert(json?.outputs?.parseStatus === 'SUCCEEDED', `${testCase.key} JSON_PARSE did not succeed`)

  const aggregate = completedNode('aggregate_1')
  assert(aggregate?.outputs?.selected === testCase.expected.aggregate, `${testCase.key} VARIABLE_AGGREGATION output mismatch`)

  const assign = completedNode('assign_1')
  assert(assign?.outputs?.variable === 'route', `${testCase.key} VARIABLE_ASSIGN variable name is wrong or empty`)
  assert(assign?.outputs?.value === testCase.expected.aggregate, `${testCase.key} VARIABLE_ASSIGN did not write aggregate value`)

  const code = completedNode('code_1')
  assert(code?.outputs?.codeToken === testCase.expected.codeToken, `${testCase.key} CODE did not combine JSON + flow variables`)

  const llm = completedNode('llm_1')
  assert(llm?.outputs?.answer === testCase.expected.llmAnswer, `${testCase.key} LLM did not echo CODE-derived token`)
  assert(String(llm?.outputs?.__debug?.llm?.input?.model || '').includes('qwen/qwen3.5-9b'), `${testCase.key} LLM model was not qwen/qwen3.5-9b`)
  assert(!String(llm?.outputs?.answer || '').includes('LLM mock:'), `${testCase.key} LLM used mock output`)

  const agent = completedNode('agent_call_1')
  assert(agent?.outputs?.agentAnswer === testCase.expected.agentAnswer, `${testCase.key} AGENT did not depend on LLM output`)

  const executeWorkflow = completedNode('execute_workflow_1')
  assert(executeWorkflow?.outputs?.childSummary === testCase.expected.childSummary, `${testCase.key} child workflow did not depend on AGENT output`)

  const forbidden = JSON.stringify({ result, nodes })
  assert(!forbidden.includes('暂无回复内容'), `${testCase.key} backend state contains empty reply placeholder`)
  return { result, nodes }
}

async function runDeepTreeCase(tab, baseUrl, testCase, index, outputDir) {
  await tab.goto(`${baseUrl}/chatflows/${testCase.chatflow.id}/canvas`)
  await tab.playwright.waitForLoadState({ state: 'load', timeoutMs: 30000 }).catch(() => undefined)
  await tab.playwright.getByText(testCase.chatflow.name, { exact: false }).waitFor({ state: 'visible', timeoutMs: 30000 })

  const runButton = await visibleRunButton(tab.playwright, `${testCase.key} run`)
  await runButton.click({})
  const panel = await unique(tab.playwright.getByTestId('test-run-panel'), `${testCase.key} run panel`)
  await panel.waitFor({ state: 'visible', timeoutMs: 15000 })
  const input = await unique(panel.getByTestId('chatflow-run-message-input'), `${testCase.key} message input`)
  await input.fill(testCase.message, {})
  const send = await unique(panel.getByRole('button', { name: '发送消息', exact: true }), `${testCase.key} send button`)
  await send.click({})

  const question = await waitForVisibleText(tab, testCase.graph.questionPrompt, { source: 'any', timeoutMs: 180000 })
  const runId = runIdFromText(question.haystack, testCase.key)
  await fillResumeCard(tab, testCase.questionAnswer, `${testCase.key} question`)
  await waitForVisibleText(tab, testCase.expectedHumanPrompt, { source: 'any', timeoutMs: 180000 })
  await fillResumeCard(tab, testCase.humanAnswer, `${testCase.key} human`)

  let finalHaystack = ''
  for (const fragment of testCase.expectedFragments) {
    const visible = await waitForVisibleText(tab, fragment, { source: 'any', timeoutMs: 180000 })
    finalHaystack = visible.haystack
  }
  assert(!finalHaystack.includes('INTENT_FALLBACK_SHOULD_NOT_APPEAR'), `${testCase.key} incorrectly took intent fallback`)
  assert(!finalHaystack.includes('SELECTOR_FALLBACK_SHOULD_NOT_APPEAR'), `${testCase.key} incorrectly took selector fallback`)

  const runtime = await assertRuntimeNodes(baseUrl, runId, testCase)
  const screenshotPath = `${outputDir}/inapp-chatflow-deep-tree-uat-${String(index + 1).padStart(2, '0')}-${testCase.key}.png`
  await screenshot(tab, screenshotPath)
  return {
    key: testCase.key,
    title: testCase.title,
    chatflowId: testCase.chatflow.id,
    runId,
    passed: true,
    requiredTypes,
    finalOutput: runtime.result.output,
    runtimeNodeCount: runtime.nodes.length,
    screenshot: screenshotPath,
  }
}

export async function runInAppChatflowDeepTreeUat(options = {}) {
  const browser = options.browser || globalThis.browser
  assert(browser, 'in-app Browser is required')
  const baseUrl = options.baseUrl || defaultBaseUrl
  const outputDir = options.outputDir || '/Users/vincento/work/develop/hify/output/playwright'
  await mkdir(outputDir, { recursive: true })
  const tab = options.tab || await ensureVisibleBrowser(browser)
  globalThis.tab = tab
  const fixtures = await createFixtures(baseUrl)
  const results = []
  const selectedCases = fixtures.cases
    .map((testCase, index) => ({ testCase, index }))
    .filter(({ testCase, index }) => {
      if (Array.isArray(options.onlyKeys) && !options.onlyKeys.includes(testCase.key)) return false
      if (typeof options.startAt === 'number' && index < options.startAt) return false
      if (typeof options.endBefore === 'number' && index >= options.endBefore) return false
      return true
    })
  for (const { testCase, index } of selectedCases) {
    const result = await runDeepTreeCase(tab, baseUrl, testCase, index, outputDir)
    results.push(result)
  }
  const summaryPath = `${outputDir}/inapp-chatflow-deep-tree-uat-summary-${fixtures.stamp}.json`
  await writeFile(summaryPath, JSON.stringify({
    stamp: fixtures.stamp,
    requiredTypes,
    total: results.length,
    passed: results.length,
    results,
  }, null, 2))
  return { stamp: fixtures.stamp, summaryPath, total: results.length, passed: results.length, results }
}
