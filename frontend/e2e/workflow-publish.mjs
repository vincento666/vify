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
const name = `Workflow Publish ${Date.now()}`

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('工作流名称').fill(name)
  await page.getByRole('button', { name: '发布' }).click()

  const opsPanel = page.locator('[data-testid="workflow-ops-panel"]')
  await opsPanel.waitFor({ state: 'visible', timeout: 5000 })
  let opsText = await opsPanel.innerText()
  assert(opsText.includes('画布校验未通过'), 'Expected publish to be blocked by validation errors')

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
  await page.getByRole('button', { name: '发布' }).click()
  await opsPanel.waitFor({ state: 'visible', timeout: 5000 })
  opsText = await opsPanel.innerText()
  assert(opsText.includes('需要先完成一次成功试运行'), 'Expected publish to require a successful test run')

  await page.getByRole('button', { name: '试运行' }).click()
  const testPanel = page.locator('[data-testid="test-run-panel"]')
  await testPanel.waitFor({ state: 'visible', timeout: 5000 })
  await testPanel.getByPlaceholder('输入 userMessage').fill('hello publish gate')
  await testPanel.getByRole('button', { name: '运行', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })
  await testPanel.locator('[data-testid="workflow-run-output"]').waitFor({ state: 'visible', timeout: 10000 })

  await page.getByRole('button', { name: '发布' }).click()
  await opsPanel.waitFor({ state: 'visible', timeout: 5000 })
  await opsPanel.getByRole('button', { name: '确认发布' }).click()
  await opsPanel.getByText('PUBLISHED').waitFor({ state: 'visible', timeout: 10000 })

  await opsPanel.getByRole('button', { name: 'Open API' }).click()
  opsText = await opsPanel.innerText()
  assert(opsText.includes('/api/v1/workflows/'), 'Expected Open API tab to show workflow run endpoint')
  assert(opsText.includes('userMessage'), 'Expected Open API tab to show request sample')

  await opsPanel.getByRole('button', { name: '运行观测' }).click()
  opsText = await opsPanel.innerText()
  assert(opsText.includes('SUCCEEDED'), 'Expected observe tab to show latest successful run status')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow publish/open-api/observe e2e')
} finally {
  await browser.close()
}
