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

async function createProcessedDocument(page, kbId, marker) {
  const document = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/knowledge-bases/${kbId}/documents`, {
      multipart: {
        file: {
          name: `faq-retrieval-${marker}.txt`,
          mimeType: 'text/plain',
          buffer: Buffer.from(`Refund document says DOC_REFUND_${marker} is reviewed within 30 days.`),
        },
      },
    }),
    'upload document',
  )

  for (let index = 0; index < 30; index += 1) {
    const latest = await unwrap(await page.request.get(`${baseUrl}/api/v1/documents/${document.id}`), 'get document')
    if (latest.status === 'DONE') return latest
    assert(latest.status !== 'FAILED', `document processing failed: ${latest.errorMessage}`)
    await page.waitForTimeout(500)
  }
  throw new Error('document processing timed out')
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
  throw new Error('No enabled model found for FAQ Agent e2e')
}

async function assertAgentUsesFaq(page, kbId, marker) {
  const modelConfigId = await findEnabledModel(page)
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `FAQ Runtime Agent ${marker}`,
        description: 'structured faq agent e2e',
        systemPrompt: 'Answer from the supplied knowledge context.',
        modelConfigId,
        temperature: 0,
        maxTokens: 256,
        maxContextTurns: 2,
        knowledgeBaseId: kbId,
        knowledgeBaseIds: [kbId],
        retrievalSettings: { topK: 3, scoreThreshold: 0, rerank: false, citationStyle: 'numbered' },
        toolIds: [],
      },
    }),
    'create faq agent',
  )
  const session = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chat/sessions`, { data: { agentId: agent.id } }),
    'create chat session',
  )
  const turn = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chat/sessions/${session.id}/messages`, {
      data: { content: `refund order ${marker}`, stream: false },
    }),
    'send chat message',
  )
  const content = turn.assistantMessage.content
  assert(content.includes('References:'), `agent response should include references, got: ${content}`)
  assert(content.includes(`Use the FAQ refund portal ${marker}.`), `agent references should include FAQ answer, got: ${content}`)
}

function knowledgeFlowPayload(name, flowType, kbId, marker) {
  const queryVariable = flowType === 'CHATFLOW' ? 'sys.query' : 'userMessage'
  return {
    name,
    description: 'structured faq runtime e2e',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: {} },
      {
        nodeKey: 'knowledge_1',
        type: 'KNOWLEDGE',
        name: '知识库',
        config: {
          knowledgeBaseId: kbId,
          query: `{{start.${queryVariable}}}`,
          topK: 3,
          outputVariable: 'answer',
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'answer' } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'knowledge_1', condition: null },
      { sourceNodeKey: 'knowledge_1', targetNodeKey: 'end', condition: null },
    ],
    flowType,
  }
}

async function assertWorkflowUsesFaq(page, kbId, marker) {
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: knowledgeFlowPayload(`FAQ Runtime Workflow ${marker}`, 'WORKFLOW', kbId, marker),
    }),
    'create faq workflow',
  )
  const run = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
      data: { input: { userMessage: `refund order ${marker}` } },
    }),
    'run faq workflow',
  )
  assert(run.output.answer === `Use the FAQ refund portal ${marker}.`, `workflow should output FAQ answer, got: ${JSON.stringify(run.output)}`)
  assert(!JSON.stringify(run).includes('Knowledge mock:'), `workflow should not use knowledge mock, got: ${JSON.stringify(run)}`)
}

async function assertChatflowUsesFaq(page, kbId, marker) {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: knowledgeFlowPayload(`FAQ Runtime Chatflow ${marker}`, 'CHATFLOW', kbId, marker),
    }),
    'create faq chatflow',
  )
  const run = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs-legacy`, {
      data: {
        input: {
          'sys.query': `refund order ${marker}`,
          'sys.conversation_id': `faq-e2e-${marker}`,
          'sys.user_id': 'user-faq-e2e',
          'sys.channel': 'web',
        },
      },
    }),
    'run faq chatflow',
  )
  assert(run.output.answer === `Use the FAQ refund portal ${marker}.`, `chatflow should output FAQ answer, got: ${JSON.stringify(run.output)}`)
  assert(!JSON.stringify(run).includes('Knowledge mock:'), `chatflow should not use knowledge mock, got: ${JSON.stringify(run)}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const marker = `FAQ_${Date.now()}`
  const kb = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/knowledge-bases`, {
      data: { name: `FAQ Retrieval UAT ${marker}`, description: 'structured faq e2e' },
    }),
    'create knowledge base',
  )
  await createProcessedDocument(page, kb.id, marker)

  await page.goto(`${baseUrl}/knowledge/${kb.id}/documents`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: 'FAQ' }).click()
  await page.getByRole('button', { name: '新增 FAQ' }).click()
  await page.getByTestId('faq-question-input').fill(`How do I request refund ${marker}?`)
  await page.getByTestId('faq-answer-input').fill(`Use the FAQ refund portal ${marker}.`)
  await page.getByPlaceholder('用 | 分隔多个问法').fill(`refund order ${marker}|money back ${marker}`)
  await page.getByTestId('faq-keywords-input').fill(`refund|${marker}`)
  await page.getByTestId('faq-save-button').click()
  await page.getByText(`Use the FAQ refund portal ${marker}.`).waitFor({ state: 'visible', timeout: 10000 })

  const exported = await page.request.get(`${baseUrl}/api/v1/knowledge-bases/${kb.id}/faqs/export-csv`)
  assert(exported.ok(), `export CSV HTTP ${exported.status()}`)
  assert((await exported.text()).includes(`How do I request refund ${marker}?`), 'exported CSV should include created FAQ')

  await page.getByRole('tab', { name: '检索测试' }).click()
  await page.getByTestId('retrieval-query-input').fill(`refund order ${marker}`)
  await page.getByRole('button', { name: '测试检索' }).click()
  const firstHit = page.locator('.retrieval-hit').first()
  await firstHit.waitFor({ state: 'visible', timeout: 10000 })
  const firstText = await firstHit.innerText()
  assert(firstText.includes('FAQ'), `first hit should be FAQ, got: ${firstText}`)
  assert(
    ['精准命中', '综合', '关键词', '语义'].some(label => firstText.includes(label)),
    `first hit should explain match type, got: ${firstText}`,
  )
  assert(firstText.includes(`Use the FAQ refund portal ${marker}.`), `first hit should include FAQ answer, got: ${firstText}`)

  const resultText = await page.locator('[data-testid="retrieval-test-panel"]').innerText()
  assert(resultText.includes('文档分块'), `retrieval should include document chunk source, got: ${resultText}`)
  assert(resultText.includes(`DOC_REFUND_${marker}`), `retrieval should include document chunk content, got: ${resultText}`)

  await assertAgentUsesFaq(page, kb.id, marker)
  await assertWorkflowUsesFaq(page, kb.id, marker)
  await assertChatflowUsesFaq(page, kb.id, marker)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS knowledge faq retrieval/runtime e2e kb=${kb.id}`)
} finally {
  await browser.close()
}
