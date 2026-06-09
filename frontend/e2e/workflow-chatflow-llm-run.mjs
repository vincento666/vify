import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
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

function llmGraph({ name, marker, startVariable, isChatflow }) {
  return {
    name,
    description: 'live LLM browser e2e',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: {
          outputVariables: isChatflow
            ? ['sys.query', 'sys.conversation_id', 'sys.user_id', 'sys.channel', 'sys.round']
            : ['USER_INPUT'],
          ui: { position: { x: 120, y: 96 } },
        },
      },
      {
        nodeKey: 'llm_1',
        type: 'LLM',
        name: '大模型',
        config: {
          prompt: `Return exactly this token and nothing else: ${marker}. User input: {{start.${startVariable}}}`,
          outputVariable: 'answer',
          ui: { position: { x: 640, y: 96 } },
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 1160, y: 96 } } },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
      { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
    ],
  }
}

async function createFlow(page, path, payload) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/${path}`, { data: payload }),
    `create ${path}`,
  )
}

async function waitForPanelOutcome(page, panel, successLocator) {
  const providerFailure = panel.getByText(/LLM provider request failed|Workflow LLM agent/)
  const outcome = await Promise.race([
    successLocator.waitFor({ state: 'visible', timeout: 60000 }).then(() => 'success').catch(() => ''),
    providerFailure.waitFor({ state: 'visible', timeout: 60000 }).then(() => 'provider-error').catch(() => ''),
  ])
  assert(outcome, `Expected run output or provider error, got: ${await panel.innerText()}`)
  return outcome
}

async function assertProviderErrorPanel(panel, label) {
  const panelText = await panel.innerText()
  assert(panelText.includes('校验失败'), `Expected ${label} panel to expose validation error, got: ${panelText}`)
  assert(
    panelText.includes('LLM provider request failed') || panelText.includes('Workflow LLM agent'),
    `Expected ${label} panel to explain provider failure, got: ${panelText}`,
  )
  assert(!panelText.includes('LLM mock:'), `Expected ${label} provider error path to avoid mock fallback, got: ${panelText}`)
  assert(await panel.locator('.run-result').count() === 0, `Expected ${label} panel to omit raw JSON code block`)
}

async function runWorkflowUat(page) {
  const marker = `WORKFLOW_LIVE_${Date.now()}`
  const workflow = await createFlow(
    page,
    'workflows',
    llmGraph({ name: `Workflow LLM UAT ${marker}`, marker, startVariable: 'USER_INPUT', isChatflow: false }),
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.canvas-actions').getByRole('button', { name: '试运行', exact: true }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByPlaceholder('输入 userMessage').fill(marker)
  await panel.getByRole('button', { name: '运行', exact: true }).click()

  const output = page.locator('[data-testid="workflow-run-output"]')
  const outcome = await waitForPanelOutcome(page, panel, output)
  if (outcome === 'provider-error') {
    await assertProviderErrorPanel(panel, 'workflow LLM')
    if (workflowScreenshotPath) {
      await page.screenshot({ path: workflowScreenshotPath, fullPage: true })
    }
    return
  }
  const outputText = await output.innerText()
  const panelText = await panel.innerText()
  assert(panelText.includes('SUCCEEDED'), 'Expected workflow LLM test run to succeed')
  assert(outputText.includes(marker), `Expected live workflow LLM token, got: ${outputText}`)
  assert(!outputText.includes('LLM mock:'), `Expected workflow to avoid mock output, got: ${outputText}`)
  assert(await panel.locator('.run-result').count() === 0, 'Expected workflow run panel to omit raw JSON code block')
  if (workflowScreenshotPath) {
    await page.screenshot({ path: workflowScreenshotPath, fullPage: true })
  }
}

async function runChatflowUat(page) {
  const marker = `CHATFLOW_LIVE_${Date.now()}`
  const chatflow = await createFlow(
    page,
    'chatflows',
    llmGraph({ name: `Chatflow LLM UAT ${marker}`, marker, startVariable: 'sys.query', isChatflow: true }),
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '对话试运行' }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByPlaceholder('输入消息').fill(marker)
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()

  const assistant = page.locator('[data-testid="chatflow-assistant-message"]')
  const outcome = await waitForPanelOutcome(page, panel, assistant)
  if (outcome === 'provider-error') {
    await assertProviderErrorPanel(panel, 'chatflow LLM')
    if (chatflowScreenshotPath) {
      await page.screenshot({ path: chatflowScreenshotPath, fullPage: true })
    }
    return
  }
  const assistantText = await assistant.last().innerText()
  const panelText = await panel.innerText()
  assert(panelText.includes('SUCCEEDED'), 'Expected chatflow LLM test run to succeed')
  assert(assistantText.includes(marker), `Expected live chatflow LLM token, got: ${assistantText}`)
  assert(!assistantText.includes('LLM mock:'), `Expected chatflow to avoid mock output, got: ${assistantText}`)
  assert(await panel.locator('.run-result').count() === 0, 'Expected chatflow run panel to omit raw JSON code block')
  if (chatflowScreenshotPath) {
    await page.screenshot({ path: chatflowScreenshotPath, fullPage: true })
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await runWorkflowUat(page)
  await runChatflowUat(page)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow/chatflow LLM canvas run e2e')
} finally {
  await browser.close()
}
