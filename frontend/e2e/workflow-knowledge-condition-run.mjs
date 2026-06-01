import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const workflowScreenshotPath = process.env.HIFY_E2E_WORKFLOW_SCREENSHOT
const workflowKbScreenshotPath = process.env.HIFY_E2E_WORKFLOW_KB_SCREENSHOT
const chatflowScreenshotPath = process.env.HIFY_E2E_CHATFLOW_SCREENSHOT
const chatflowKbScreenshotPath = process.env.HIFY_E2E_CHATFLOW_KB_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function createKnowledgeBase(page, marker) {
  const kb = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/knowledge-bases`, {
      data: { name: `KB condition UAT ${marker}`, description: 'browser e2e' },
    }),
    'create knowledge base',
  )
  const content = Buffer.from(
    [
      `Refund policy ${marker}.`,
      `The approved refund answer is KB_CONDITION_${marker}.`,
    ].join(' '),
  )
  const document = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/knowledge-bases/${kb.id}/documents`, {
      multipart: {
        file: {
          name: `kb-condition-${marker}.txt`,
          mimeType: 'text/plain',
          buffer: content,
        },
      },
    }),
    'upload knowledge document',
  )

  for (let index = 0; index < 30; index += 1) {
    const latest = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/documents/${document.id}`),
      'get knowledge document',
    )
    if (latest.status === 'DONE') return kb
    assert(latest.status !== 'FAILED', `knowledge document failed: ${latest.errorMessage}`)
    await page.waitForTimeout(500)
  }
  throw new Error('knowledge document did not finish processing')
}

function graphPayload({ name, flowType, kbId, marker, startVariable }) {
  const knowledgeQuery = `refund policy ${marker}`
  const defaultOutput = `DEFAULT_BRANCH_${marker}`
  return {
    name,
    description: 'condition and knowledge browser e2e',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: { outputVariables: [startVariable], ui: { position: { x: 120, y: 96 } } },
      },
      {
        nodeKey: 'router',
        type: 'CONDITION',
        name: '条件',
        config: {
          expression: `{{start.${startVariable}}}`,
          outputVariable: 'route',
          ui: { position: { x: 380, y: 160 } },
        },
      },
      {
        nodeKey: 'kb',
        type: 'KNOWLEDGE',
        name: '知识库',
        config: {
          query: knowledgeQuery,
          knowledgeBaseId: kbId,
          outputVariable: 'answer',
          ui: { position: { x: 640, y: 96 } },
        },
      },
      {
        nodeKey: 'fallback',
        type: 'END',
        name: '默认结束',
        config: {
          outputVariable: 'answer',
          output: defaultOutput,
          ui: { position: { x: 640, y: 300 } },
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: { outputVariable: 'answer', ui: { position: { x: 900, y: 96 } } },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'router', condition: null },
      { sourceNodeKey: 'router', targetNodeKey: 'fallback', condition: null },
      { sourceNodeKey: 'router', targetNodeKey: 'kb', condition: 'kb' },
      { sourceNodeKey: 'kb', targetNodeKey: 'end', condition: null },
    ],
    flowType,
  }
}

async function createWorkflow(page, payload, isChatflow) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/${isChatflow ? 'chatflows' : 'workflows'}`, {
      data: payload,
    }),
    isChatflow ? 'create chatflow' : 'create workflow',
  )
}

async function runWorkflowPanel(page, input, expected) {
  const textarea = page.getByPlaceholder('输入 userMessage')
  await textarea.fill(input)
  await page.getByRole('button', { name: '运行', exact: true }).click()
  const output = page.locator('[data-testid="workflow-run-output"]')
  await output.waitFor({ state: 'visible', timeout: 20000 })
  const text = await output.innerText()
  assert(text.includes(expected), `Expected workflow output ${expected}, got: ${text}`)
  assert(!text.includes('Knowledge mock:'), `Expected workflow to avoid knowledge mock, got: ${text}`)
}

async function runChatflowPanel(page, input, expected) {
  const textarea = page.getByPlaceholder('输入用户消息')
  await textarea.fill(input)
  await page.getByRole('button', { name: '运行', exact: true }).click()
  const assistant = page.locator('[data-testid="chatflow-assistant-message"]')
  await assistant.waitFor({ state: 'visible', timeout: 20000 })
  const text = await assistant.innerText()
  assert(text.includes(expected), `Expected chatflow output ${expected}, got: ${text}`)
  assert(!text.includes('Knowledge mock:'), `Expected chatflow to avoid knowledge mock, got: ${text}`)
}

async function runWorkflowUat(page, kb, marker) {
  const workflow = await createWorkflow(
    page,
    graphPayload({
      name: `Workflow KB Condition UAT ${marker}`,
      flowType: 'WORKFLOW',
      kbId: kb.id,
      marker,
      startVariable: 'USER_INPUT',
    }),
    false,
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '试运行' }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await runWorkflowPanel(page, 'kb', `KB_CONDITION_${marker}`)
  if (workflowKbScreenshotPath) await page.screenshot({ path: workflowKbScreenshotPath, fullPage: true })
  await runWorkflowPanel(page, 'other', `DEFAULT_BRANCH_${marker}`)
  assert(await panel.locator('.run-result').count() === 0, 'Expected workflow panel to omit raw JSON code block')
  if (workflowScreenshotPath) await page.screenshot({ path: workflowScreenshotPath, fullPage: true })
}

async function runChatflowUat(page, kb, marker) {
  const chatflow = await createWorkflow(
    page,
    graphPayload({
      name: `Chatflow KB Condition UAT ${marker}`,
      flowType: 'CHATFLOW',
      kbId: kb.id,
      marker,
      startVariable: 'sys.query',
    }),
    true,
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '对话试运行' }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await runChatflowPanel(page, 'kb', `KB_CONDITION_${marker}`)
  if (chatflowKbScreenshotPath) await page.screenshot({ path: chatflowKbScreenshotPath, fullPage: true })
  await runChatflowPanel(page, 'other', `DEFAULT_BRANCH_${marker}`)
  assert(await panel.locator('.run-result').count() === 0, 'Expected chatflow panel to omit raw JSON code block')
  if (chatflowScreenshotPath) await page.screenshot({ path: chatflowScreenshotPath, fullPage: true })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const marker = `KC_${Date.now()}`
  const kb = await createKnowledgeBase(page, marker)
  await runWorkflowUat(page, kb, marker)
  await runChatflowUat(page, kb, marker)
  console.log('PASS workflow/chatflow knowledge condition canvas run e2e')
} finally {
  await browser.close()
}
