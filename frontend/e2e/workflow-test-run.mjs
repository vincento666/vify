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

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Workflow Test Run ${Date.now()}`

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('工作流名称').fill(name)
  await page.getByRole('button', { name: '试运行' }).click()

  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByText('校验失败').waitFor({ state: 'visible', timeout: 5000 })
  const validationText = await panel.innerText()
  assert(
    validationText.includes('START must connect to END through at least one path'),
    'Expected disconnected graph to fail validation before a test run',
  )

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })
  const workflowId = Number(page.url().match(/\/workflows\/(\d+)\/canvas/)?.[1])
  assert(Number.isFinite(workflowId), 'Expected workflow id after saving disconnected graph')
  await unwrap(
    await page.request.put(`${baseUrl}/api/v1/workflows/${workflowId}`, {
      data: {
        name,
        description: 'connected by e2e setup',
        nodes: [
          {
            nodeKey: 'start',
            type: 'START',
            name: '开始',
            config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 96 } } },
          },
          {
            nodeKey: 'end',
            type: 'END',
            name: '结束',
            config: { outputVariable: 'output', output: '{{start.USER_INPUT}}', ui: { position: { x: 780, y: 96 } } },
          },
        ],
        edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
      },
    }),
    'connect workflow graph',
  )
  await page.reload({ waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '试运行' }).click()
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByPlaceholder('输入 userMessage').fill('hello from e2e')
  await panel.getByRole('button', { name: '运行', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })

  const result = panel.locator('[data-testid="workflow-run-output"]')
  await result.waitFor({ state: 'visible', timeout: 10000 })
  const resultText = await result.innerText()
  const panelText = await panel.innerText()
  assert(panelText.includes('SUCCEEDED'), 'Expected successful workflow test run status')
  assert(resultText.includes('output'), 'Expected workflow test run output field')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow test run e2e')
} finally {
  await browser.close()
}
