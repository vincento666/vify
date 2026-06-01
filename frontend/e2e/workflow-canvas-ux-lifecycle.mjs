import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const workflowScreenshotPath = process.env.HIFY_E2E_WORKFLOW_SCREENSHOT
const chatflowScreenshotPath = process.env.HIFY_E2E_CHATFLOW_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function createFlow(page, path, data) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/${path}`, { data }),
    `create ${path}`,
  )
}

async function getFlow(page, path, id) {
  return unwrap(
    await page.request.get(`${baseUrl}/api/v1/${path}/${id}`),
    `get ${path}`,
  )
}

async function runWorkflowUx(page, marker) {
  const workflow = await createFlow(page, 'workflows', {
    name: `Workflow Canvas UX ${marker}`,
    description: 'browser e2e',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 500, y: 500 } } },
      },
      {
        nodeKey: 'condition_1',
        type: 'CONDITION',
        name: '条件',
        config: { expression: '{{start.USER_INPUT}}', outputVariable: 'route', ui: { position: { x: 200, y: 420 } } },
      },
      {
        nodeKey: 'llm_1',
        type: 'LLM',
        name: '大模型',
        config: { prompt: `Return ${marker}`, outputVariable: 'answer', ui: { position: { x: 180, y: 160 } } },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: { outputVariable: 'answer', output: '{{llm_1.answer}}', ui: { position: { x: 90, y: 320 } } },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'condition_1', condition: null },
      { sourceNodeKey: 'condition_1', targetNodeKey: 'llm_1', condition: 'run' },
      { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
    ],
  })

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  assert(await page.getByRole('button', { name: '开放', exact: true }).count() === 1, 'Expected 开放 lifecycle tab')
  assert(await page.getByRole('button', { name: 'Open API', exact: true }).count() === 0, 'Expected topbar Open API duplicate to be removed')
  assert(await page.getByRole('button', { name: '快速连线', exact: true }).count() === 0, 'Expected 快速连线 action to be removed')

  await page.getByLabel('折叠侧栏').click()
  assert(await page.locator('[data-testid="canvas-resource-panel"]').count() === 0, 'Expected canvas side panel to collapse')
  await page.getByLabel('展开侧栏').click()
  await page.locator('[data-testid="canvas-resource-panel"]').waitFor({ state: 'visible', timeout: 5000 })

  await page.getByRole('button', { name: '自动布局' }).click()
  const saveResponse = page.waitForResponse((response) =>
    response.url().includes(`/api/v1/workflows/${workflow.id}`)
      && response.request().method() === 'PUT',
  )
  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await saveResponse
  const saved = await getFlow(page, 'workflows', workflow.id)
  const byKey = new Map(saved.nodes.map((node) => [node.nodeKey, node]))
  assert(byKey.get('start').config.ui.position.x < byKey.get('condition_1').config.ui.position.x, 'Expected START to be left of CONDITION after auto layout')
  assert(byKey.get('condition_1').config.ui.position.x < byKey.get('llm_1').config.ui.position.x, 'Expected CONDITION to be left of LLM after auto layout')
  assert(byKey.get('llm_1').config.ui.position.x < byKey.get('end').config.ui.position.x, 'Expected LLM to be left of END after auto layout')
  assert(
    saved.edges.some((edge) => edge.sourceNodeKey === 'condition_1' && edge.targetNodeKey === 'llm_1' && edge.condition === 'run'),
    'Expected conditional edge to survive auto layout and save',
  )

  if (workflowScreenshotPath) await page.screenshot({ path: workflowScreenshotPath, fullPage: true })
}

async function runChatflowUx(page, marker) {
  const openingText = `开场白_${marker}`
  const guideQuestion = `引导问题_${marker}`
  const chatflow = await createFlow(page, 'chatflows', {
    name: `Chatflow Runtime UX ${marker}`,
    description: 'browser e2e',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: {
          outputVariables: ['sys.query', 'sys.conversation_id', 'sys.user_id', 'sys.channel', 'sys.round'],
          openingText,
          guideQuestions: [guideQuestion],
          ui: { position: { x: 120, y: 96 } },
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: { outputVariable: 'output', output: '{{start.sys.query}}', ui: { position: { x: 780, y: 96 } } },
      },
    ],
    edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
  })

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '对话试运行' }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByTestId('chatflow-opening-message').waitFor({ state: 'visible', timeout: 5000 })
  assert((await panel.getByTestId('chatflow-opening-message').innerText()).includes(openingText), 'Expected opening text to appear before a user run')

  await panel.getByTestId('chatflow-guide-question').click()
  assert(await panel.getByPlaceholder('输入用户消息').inputValue() === guideQuestion, 'Expected guide question to fill the chat input')

  await panel.getByRole('button', { name: '运行', exact: true }).click()
  const assistant = panel.getByTestId('chatflow-assistant-message')
  await assistant.waitFor({ state: 'visible', timeout: 10000 })
  const panelText = await panel.innerText()
  assert(panelText.includes('SUCCEEDED'), 'Expected chatflow run to succeed')
  assert(panelText.includes(openingText), 'Expected opening text to remain in the conversation result')
  assert((await assistant.innerText()).includes(guideQuestion), 'Expected chatflow output to use the guide-question input')
  assert(await panel.locator('.run-result').count() === 0, 'Expected chatflow trial panel to avoid raw JSON code block')

  if (chatflowScreenshotPath) await page.screenshot({ path: chatflowScreenshotPath, fullPage: true })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const marker = `UX_${Date.now()}`
  await runWorkflowUx(page, marker)
  await runChatflowUx(page, marker)
  console.log('PASS workflow/chatflow canvas UX lifecycle e2e')
} finally {
  await browser.close()
}
