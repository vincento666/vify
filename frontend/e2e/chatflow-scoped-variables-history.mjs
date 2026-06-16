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

async function createVariableChatflow(page, stamp) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `018.3 Scoped Variable ${stamp}`,
      description: 'chatflow scoped variables e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        { nodeKey: 'question_1', type: 'QUESTION', name: '问题', config: { question: '主题？', outputVariable: 'answer', ui: { position: { x: 480, y: 180 } } } },
        {
          nodeKey: 'assign_1',
          type: 'VARIABLE_ASSIGN',
          name: '变量赋值',
          config: {
            targetScope: 'conversation',
            targetVariable: 'topic',
            source: '{{question_1.answer}}',
            writeMode: 'set',
            outputParameters: [{ name: 'assigned', type: 'string' }],
            ui: { position: { x: 820, y: 180 } },
          },
        },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'topic={{conversation.topic}}', ui: { position: { x: 1160, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'question_1', condition: null },
        { sourceNodeKey: 'question_1', targetNodeKey: 'assign_1', condition: null },
        { sourceNodeKey: 'assign_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create variable chatflow')
}

async function createHistoryChatflow(page, stamp) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `018.3 History ${stamp}`,
      description: 'chatflow persisted history e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        { nodeKey: 'message_1', type: 'MESSAGE', name: '消息', config: { content: '我叫 Ada，咨询 {{start.sys.query}}', outputVariable: 'content', ui: { position: { x: 500, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{message_1.content}}', ui: { position: { x: 880, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
        { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create history chatflow')
}

async function createScopeInputChatflow(page, stamp) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `018.3 Scope Inputs ${stamp}`,
      description: 'chatflow scope inputs e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{sys.query}}|{{user.tier}}|{{channel.name}}|{{global.locale}}|{{start.externalId}}', ui: { position: { x: 520, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create scope input chatflow')
}

async function replaceWithHistoryCollection(page, chatflowId, stamp) {
  await unwrap(await page.request.put(`${baseUrl}/api/v1/chatflows/${chatflowId}`, {
    data: {
      name: `018.3 History ${stamp}`,
      description: 'chatflow persisted history e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'collect_1',
          type: 'INFORMATION_COLLECTION',
          name: '信息收集',
          config: {
            inputSource: '{{start.sys.query}}',
            outputVariable: 'collected',
            includeHistory: true,
            maxRounds: 1,
            fields: [
              { name: 'name', type: 'string', required: true, description: '姓名' },
              { name: 'phone', type: 'string', required: true, description: '手机号' },
            ],
            ui: { position: { x: 500, y: 180 } },
          },
        },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{collect_1.name}}|{{collect_1.phone}}', ui: { position: { x: 880, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'collect_1', condition: null },
        { sourceNodeKey: 'collect_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'replace history chatflow')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()

  const variableChatflow = await createVariableChatflow(page, stamp)
  const interrupted = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${variableChatflow.id}/runs`, {
    data: { input: { 'sys.query': 'start', 'sys.conversation_id': `conv-variable-${stamp}` } },
  }), 'start variable chatflow')
  assert(interrupted.status === 'INTERRUPTED', 'Expected variable chatflow to interrupt')

  const resumeEventId = interrupted.events[interrupted.events.length - 1].id
  const resumed = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${variableChatflow.id}/runs/${interrupted.runId}/resume`, {
    data: { eventId: resumeEventId, resumeData: { answer: 'refund' } },
  }), 'resume variable chatflow')
  assert(resumed.status === 'SUCCEEDED', 'Expected resumed variable chatflow succeeded')
  assert(resumed.output.final === 'topic=refund', 'Expected conversation variable rendered in end node')

  const session = await unwrap(await page.request.get(`${baseUrl}/api/v1/chatflows/${variableChatflow.id}/sessions/${interrupted.sessionId}`), 'get variable session')
  assert(session.variables.conversation.topic === 'refund', 'Expected persisted conversation variable topic')
  assert(session.expiresAt, 'Expected session expiration metadata')

  const scopeChatflow = await createScopeInputChatflow(page, stamp)
  const scopeRun = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${scopeChatflow.id}/runs`, {
    data: {
      input: {
        'sys.query': 'refund',
        'sys.conversation_id': `conv-scope-${stamp}`,
        'user.tier': 'vip',
        'channel.name': 'web',
        'global.locale': 'zh-CN',
        externalId: 'ticket-0183',
      },
    },
  }), 'run scope input chatflow')
  assert(scopeRun.status === 'SUCCEEDED', 'Expected scope input run succeeded')
  assert(scopeRun.output.final === 'refund|vip|web|zh-CN|ticket-0183', 'Expected scoped input variables rendered')
  const scopeSession = await unwrap(await page.request.get(`${baseUrl}/api/v1/chatflows/${scopeChatflow.id}/sessions/conv-scope-${stamp}`), 'get scope input session')
  assert(scopeSession.variables.sys.query === 'refund', 'Expected sys scope persisted')
  assert(scopeSession.variables.user.tier === 'vip', 'Expected user scope persisted')
  assert(scopeSession.variables.channel.name === 'web', 'Expected channel scope persisted')
  assert(scopeSession.variables.global.locale === 'zh-CN', 'Expected global scope persisted')

  const conversationId = `conv-history-${stamp}`
  const historyChatflow = await createHistoryChatflow(page, stamp)
  const first = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${historyChatflow.id}/runs`, {
    data: { input: { 'sys.query': '订单问题', 'sys.conversation_id': conversationId } },
  }), 'first history chatflow run')
  assert(first.status === 'SUCCEEDED', 'Expected first history message run succeeded')

  await replaceWithHistoryCollection(page, historyChatflow.id, stamp)
  const second = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${historyChatflow.id}/runs`, {
    data: { input: { 'sys.query': '手机号 13800138000', 'sys.conversation_id': conversationId } },
  }), 'second history chatflow run')
  assert(second.status === 'SUCCEEDED', 'Expected history collection run succeeded')
  assert(second.output.final === 'Ada|13800138000', 'Expected persisted history and current input merged')

  await page.goto(`${baseUrl}/chatflows/${historyChatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-information_collection, .coze-node.node-information-collection').waitFor({ state: 'visible', timeout: 10000 })
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS chatflow scoped variables history e2e variable=${variableChatflow.id} history=${historyChatflow.id}`)
} finally {
  await browser.close()
}
