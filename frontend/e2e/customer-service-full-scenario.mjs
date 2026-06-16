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

async function findEnabledModel(page) {
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      if (String(provider.baseUrl || '').startsWith('mock://')) continue
      for (const model of provider.models ?? []) {
        if (model.enabled) return model.id
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  throw new Error('No enabled non-mock model found for customer-service scenario')
}

async function createFaqKnowledge(page, marker) {
  const kb = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/knowledge-bases`, {
      data: { name: `CS FAQ ${marker}`, description: 'customer service scenario faq' },
    }),
    'create knowledge base',
  )
  await unwrap(
    await page.request.post(`${baseUrl}/api/v1/knowledge-bases/${kb.id}/faqs`, {
      data: {
        question: `How does refund work ${marker}?`,
        answer: `FAQ_REFUND_${marker}: refund requests are reviewed within 2 business days.`,
        alternativeQuestions: [`refund policy ${marker}`, `refund A-100 ${marker}`],
        keywords: ['refund', marker],
        category: 'refund',
        priority: 10,
      },
    }),
    'create faq',
  )
  return kb
}

async function createSubworkflow(page, marker) {
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `CS Child Workflow ${marker}`,
        description: 'customer service child workflow',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: {} },
          {
            nodeKey: 'format_1',
            type: 'TEXT_PROCESS',
            name: '文本处理',
            config: {
              operation: 'format_template',
              template: `SUBFLOW_${marker}: audit {{start.ticket}}`,
              outputParameters: [{ name: 'summary', type: 'string' }],
            },
          },
          {
            nodeKey: 'end',
            type: 'END',
            name: '结束',
            config: { outputVariable: 'summary', output: '{{format_1.summary}}' },
          },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'format_1', condition: null },
          { sourceNodeKey: 'format_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create child workflow',
  )
  await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/publish`), 'publish child workflow')
  return workflow
}

async function createAgent(page, marker) {
  const modelConfigId = await findEnabledModel(page)
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `CS Agent ${marker}`,
        description: 'customer service agent call target',
        systemPrompt:
          `Always include marker ${marker}, the order id, and summarize any FAQ/tool/subflow context in one concise sentence.`,
        modelConfigId,
        temperature: 0,
        maxTokens: 256,
        maxContextTurns: 4,
        toolIds: [],
      },
    }),
    'create scenario agent',
  )
}

function chatflowPayload({ marker, kbId, serverId, childWorkflowId, agentId }) {
  return {
    name: `CS Full Scenario ${marker}`,
    description: 'full customer service scenario',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query', 'sys.conversation_id', 'sys.user_id', 'sys.channel'] } },
      {
        nodeKey: 'intent_1',
        type: 'INTENT_RECOGNITION',
        name: '意图识别',
        config: {
          inputSource: '{{start.sys.query}}',
          intents: [
            { key: 'refund', name: '退款', examples: ['refund', '退款', 'A-100'] },
            { key: 'human', name: '人工', examples: ['human', '人工', '客服'] },
          ],
          defaultIntent: 'refund',
          classifierMode: 'fake',
          includeHistory: 'true',
          outputParameters: [{ name: 'intent', type: 'string' }],
        },
      },
      {
        nodeKey: 'info_1',
        type: 'INFORMATION_COLLECTION',
        name: '信息收集',
        config: {
          inputSource: '{{start.sys.query}}',
          outputVariable: 'profile',
          collectionKey: 'profile',
          includeHistory: true,
          extractorMode: 'fake',
          maxRounds: 3,
          streamOutput: 'enabled',
          fields: [
            { name: 'name', type: 'string', required: true, description: '姓名', targetScope: 'conversation', targetVariable: 'customer_name' },
            { name: 'phone', type: 'string', required: true, description: '手机号' },
          ],
        },
      },
      {
        nodeKey: 'knowledge_1',
        type: 'KNOWLEDGE',
        name: '知识库',
        config: {
          knowledgeBaseId: kbId,
          query: `refund A-100 ${marker}`,
          topK: 3,
          outputVariable: 'faqAnswer',
        },
      },
      {
        nodeKey: 'tool_call_1',
        type: 'TOOL_CALL',
        name: '工具调用',
        config: {
          resourceType: 'MCP_TOOL',
          resourceId: `mcp:${serverId}:lookup_order`,
          toolName: 'lookup_order',
          serverIds: [serverId],
          inputMappings: [{ name: 'orderId', valueMode: 'literal', value: 'A-100', required: true }],
          timeoutMs: 30000,
          retryCount: 0,
          errorBehavior: 'fail',
          outputParameters: [
            { name: 'result', type: 'string' },
            { name: 'success', type: 'boolean' },
            { name: 'evidence', type: 'object' },
          ],
        },
      },
      {
        nodeKey: 'execute_workflow_1',
        type: 'EXECUTE_WORKFLOW',
        name: '工作流',
        config: {
          targetWorkflowId: childWorkflowId,
          inputMappings: [{ name: 'ticket', valueMode: 'literal', value: 'A-100', required: true }],
          outputMappings: [{ source: 'summary', target: 'childSummary' }],
          outputParameters: [
            { name: 'childSummary', type: 'string' },
            { name: 'nestedRunId', type: 'number' },
            { name: 'status', type: 'string' },
          ],
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
              value:
                `Marker ${marker}. Order A-100. FAQ={{knowledge_1.faqAnswer}} Tool={{tool_call_1.result}} Subflow={{execute_workflow_1.childSummary}}`,
              required: true,
            },
          ],
          historyMode: 'include',
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
        nodeKey: 'message_1',
        type: 'MESSAGE',
        name: '消息',
        config: {
          content:
            `客服结果 ${marker}: {{knowledge_1.faqAnswer}} | {{tool_call_1.result}} | {{execute_workflow_1.childSummary}} | {{agent_call_1.agentAnswer}}`,
          outputVariable: 'content',
          streamOutput: 'enabled',
        },
      },
      {
        nodeKey: 'transfer_to_human_1',
        type: 'TRANSFER_TO_HUMAN',
        name: '转人工',
        config: {
          message: `HANDOFF_${marker}: 已转人工客服。`,
          queue: 'vip-support',
          reason: 'manual_request',
          priority: 'high',
          slaMinutes: 15,
          outputParameters: [
            { name: 'handoff_id', type: 'number' },
            { name: 'handoff_status', type: 'string' },
            { name: 'queue', type: 'string' },
          ],
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{message_1.content}}' } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'intent_1', condition: null },
      { sourceNodeKey: 'intent_1', targetNodeKey: 'info_1', condition: 'refund' },
      { sourceNodeKey: 'intent_1', targetNodeKey: 'transfer_to_human_1', condition: 'human' },
      { sourceNodeKey: 'info_1', targetNodeKey: 'knowledge_1', condition: null },
      { sourceNodeKey: 'knowledge_1', targetNodeKey: 'tool_call_1', condition: null },
      { sourceNodeKey: 'tool_call_1', targetNodeKey: 'execute_workflow_1', condition: null },
      { sourceNodeKey: 'execute_workflow_1', targetNodeKey: 'agent_call_1', condition: null },
      { sourceNodeKey: 'agent_call_1', targetNodeKey: 'message_1', condition: null },
      { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
      { sourceNodeKey: 'transfer_to_human_1', targetNodeKey: 'end', condition: null },
    ],
  }
}

async function createScenario(page, marker) {
  const kb = await createFaqKnowledge(page, marker)
  const server = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
      data: { name: `CS MCP ${marker}`, endpoint: 'mock://tools', description: 'customer service tool server' },
    }),
    'create mcp server',
  )
  const childWorkflow = await createSubworkflow(page, marker)
  const agent = await createAgent(page, marker)
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: chatflowPayload({ marker, kbId: kb.id, serverId: server.id, childWorkflowId: childWorkflow.id, agentId: agent.id }),
    }),
    'create scenario chatflow',
  )
  return { kb, server, childWorkflow, agent, chatflow }
}

async function publishAndEnableChannels(page, chatflowId) {
  await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflowId}/publish`), 'publish chatflow')
  await unwrap(
    await page.request.put(`${baseUrl}/api/v1/chatflows/${chatflowId}/channels/api`, {
      data: { enabled: true, displayName: 'REST API', config: { defaultUserId: 'api-user' } },
    }),
    'enable api channel',
  )
  await unwrap(
    await page.request.put(`${baseUrl}/api/v1/chatflows/${chatflowId}/channels/web`, {
      data: { enabled: true, displayName: 'Web Chat', config: { defaultUserId: 'web-user' } },
    }),
    'enable web channel',
  )
}

async function runIncompleteThenResume(page, chatflowId, marker) {
  const interrupted = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflowId}/channels/web/test`, {
      data: {
        message: `refund A-100 ${marker} 我叫 Ada`,
        conversationId: `cs-${marker}`,
        userId: 'cs-user',
      },
    }),
    'run web channel incomplete',
  )
  const run = interrupted.run
  assert(run.status === 'INTERRUPTED', `expected missing slot interrupt: ${JSON.stringify(interrupted)}`)
  assert(run.output.interrupt.nodeKey === 'info_1', `expected info interrupt: ${JSON.stringify(run.output)}`)
  assert(run.output.missing.includes('phone'), `expected phone missing: ${JSON.stringify(run.output)}`)
  const waitingEvent = run.events.find((event) => event.type === 'interrupt')
  assert(waitingEvent?.id, `expected interrupt event id: ${JSON.stringify(run.events)}`)

  const resumed = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflowId}/runs/${run.runId}/resume`, {
      data: { eventId: waitingEvent.id, resumeData: { answer: '手机号 13800138000' } },
    }),
    'resume customer service run',
  )
  assert(resumed.status === 'SUCCEEDED', `expected resumed success: ${JSON.stringify(resumed)}`)
  const finalText = String(resumed.output.final || '')
  for (const token of [`FAQ_REFUND_${marker}`, 'SHIPPED', `SUBFLOW_${marker}`, marker]) {
    assert(finalText.includes(token), `final output should include ${token}: ${finalText}`)
  }
  assert(!finalText.includes('Knowledge mock:'), `should not use knowledge mock: ${finalText}`)
  assert(!finalText.includes('LLM mock:'), `should not use LLM mock: ${finalText}`)
  return { interrupted: run, resumed }
}

async function runPublishedComplete(page, chatflowId, marker) {
  const published = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflowId}/published-runs`, {
      data: {
        input: {
          'sys.query': `refund A-100 ${marker} 我叫 Ada 手机号 13800138000`,
          'sys.conversation_id': `published-${marker}`,
          'sys.user_id': 'published-user',
          'sys.channel': 'api',
        },
      },
    }),
    'run published chatflow',
  )
  assert(published.status === 'SUCCEEDED', `expected published success: ${JSON.stringify(published)}`)
  assert(String(published.output.final || '').includes(`FAQ_REFUND_${marker}`), `published output should include FAQ: ${JSON.stringify(published.output)}`)
  return published
}

async function runHandoffFallback(page, chatflowId, marker) {
  const handoff = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflowId}/channels/web/test`, {
      data: {
        message: `human support please ${marker}`,
        conversationId: `handoff-${marker}`,
        userId: 'handoff-user',
      },
    }),
    'run handoff branch',
  )
  assert(handoff.run.status === 'INTERRUPTED', `expected handoff interrupt: ${JSON.stringify(handoff)}`)
  assert(String(handoff.run.output.interrupt.message || '').includes(`HANDOFF_${marker}`), `expected handoff message: ${JSON.stringify(handoff.run.output)}`)
  const tickets = await unwrap(await page.request.get(`${baseUrl}/api/v1/handoffs?status=queued&pageSize=100`), 'list handoffs')
  const ticket = tickets.list.find((item) => item.conversationId === `handoff-${marker}`)
  assert(ticket, `expected handoff ticket: ${JSON.stringify(tickets)}`)
  assert(ticket.queue === 'vip-support', `expected vip-support queue: ${JSON.stringify(ticket)}`)
  return handoff.run
}

async function assertDebug(page, chatflowId, runId, marker) {
  const debug = await unwrap(
    await page.request.get(`${baseUrl}/api/v1/chatflows/${chatflowId}/runs/${runId}/debug`),
    'get run debug',
  )
  const text = JSON.stringify(debug)
  for (const token of ['KNOWLEDGE', 'TOOL_CALL', 'EXECUTE_WORKFLOW', 'AGENT_CALL', 'MESSAGE']) {
    assert(text.includes(token), `debug should include ${token}: ${text}`)
  }
  assert(text.includes(`FAQ_REFUND_${marker}`), `debug should include FAQ evidence: ${text}`)
  assert(text.includes('lookup_order') || text.includes('SHIPPED'), `debug should include tool evidence: ${text}`)
  assert(text.includes(`SUBFLOW_${marker}`), `debug should include subflow evidence: ${text}`)
  assert(text.includes(marker), `debug should include agent marker: ${text}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const marker = `CS${Date.now()}`
  const scenario = await createScenario(page, marker)
  await publishAndEnableChannels(page, scenario.chatflow.id)

  const resumedPath = await runIncompleteThenResume(page, scenario.chatflow.id, marker)
  const publishedRun = await runPublishedComplete(page, scenario.chatflow.id, marker)
  const handoffRun = await runHandoffFallback(page, scenario.chatflow.id, marker)
  await assertDebug(page, scenario.chatflow.id, resumedPath.resumed.runId, marker)
  await assertDebug(page, scenario.chatflow.id, publishedRun.runId, marker)

  await page.goto(`${baseUrl}/chatflows/${scenario.chatflow.id}/canvas?runId=${resumedPath.resumed.runId}&debug=1`, { waitUntil: 'load' })
  const callTree = page.getByTestId('chatflow-run-call-tree')
  for (const nodeType of ['AGENT_CALL', 'TOOL_CALL', 'EXECUTE_WORKFLOW']) {
    await callTree
      .locator('button.workflow-call-tree-node')
      .filter({ hasText: `${nodeType} 成功` })
      .first()
      .waitFor({ state: 'visible', timeout: 10000 })
  }
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS customer service full scenario chatflow=${scenario.chatflow.id} run=${resumedPath.resumed.runId} publishedRun=${publishedRun.runId} handoffRun=${handoffRun.runId}`)
} finally {
  await browser.close()
}
