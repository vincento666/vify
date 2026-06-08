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

async function softCheck(errors, message, check) {
  try {
    const passed = await check()
    if (!passed) errors.push(message)
  } catch (error) {
    errors.push(`${message}: ${error instanceof Error ? error.message : String(error)}`)
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `025.4a LLM Interaction ${stamp}`,
        description: 'llm selector and prompt interaction hardening e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 220 } } } },
          { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { outputVariable: 'answer', ui: { position: { x: 520, y: 220 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 900, y: 220 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create 025.4a chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })

  const errors = []

  const modelSection = panel.getByTestId('llm-model-section')
  await modelSection.getByRole('button', { name: '模型设置', exact: true }).click()
  await page.waitForTimeout(150)
  await softCheck(errors, 'Expected model gear to open the model parameter panel', async () =>
    (await panel.getByTestId('llm-model-parameter-panel').count()) === 1,
  )
  await softCheck(errors, 'Expected model gear not to open the model selector dropdown', async () =>
    (await panel.getByTestId('llm-model-selector').count()) === 0,
  )

  const resourceSection = panel.getByTestId('llm-resource-section')
  await resourceSection.getByRole('button', { name: '添加资源', exact: true }).click()
  await page.waitForTimeout(150)
  await softCheck(errors, 'Expected LLM skill picker to use resource type tabs', async () =>
    (await resourceSection.getByTestId('llm-skill-type-tabs').count()) === 1,
  )
  await softCheck(errors, 'Expected mixed resource registry dropdown to be absent from LLM skills', async () =>
    (await resourceSection.getByTestId('workflow-resource-registry').count()) === 0,
  )

  const systemSection = panel.getByTestId('config-section-系统提示词')
  const userSection = panel.getByTestId('config-section-用户提示词')
  await softCheck(errors, 'Expected system prompt header to remove the separate variable button', async () =>
    (await systemSection.getByRole('button', { name: '变量', exact: true }).count()) === 0,
  )
  await softCheck(errors, 'Expected user prompt header to remove the separate variable button', async () =>
    (await userSection.getByRole('button', { name: '变量', exact: true }).count()) === 0,
  )

  await systemSection.locator('textarea').fill('{{')
  await page.waitForTimeout(180)
  await softCheck(errors, 'Expected typing {{ in system prompt to open the variable picker', async () =>
    (await systemSection.getByTestId('variable-picker').count()) === 1,
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  assert(errors.length === 0, errors.join('\n'))
  console.log(`PASS 025.4a LLM selector and prompt hardening e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
