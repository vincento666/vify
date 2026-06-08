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
const name = `Workflow Debug Dock ${Date.now()}`

try {
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name,
        description: 'debug dock run evidence',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 160, y: 160 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.USER_INPUT}}', ui: { position: { x: 620, y: 160 } } } },
        ],
        edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
      },
    }),
    'create debug dock workflow',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.canvas-actions').getByRole('button', { name: '试运行', exact: true }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByPlaceholder('输入 userMessage').fill('debug dock input')
  await panel.getByRole('button', { name: '运行', exact: true }).click()
  await panel.getByText('SUCCEEDED').waitFor({ state: 'visible', timeout: 10000 })

  const toolbar = page.locator('[data-testid="canvas-bottom-toolbar"]')
  await toolbar.getByRole('button', { name: '调试工具', exact: true }).click()
  const dock = page.locator('[data-testid="workflow-debug-dock"]')
  await dock.waitFor({ state: 'visible', timeout: 5000 })
  await dock.getByRole('button', { name: '调试', exact: true }).click()
  const runSummary = dock.locator('.workflow-run-summary')
  await runSummary.getByText(/^Run #/).waitFor({ state: 'visible', timeout: 8000 })
  await runSummary.getByText('SUCCEEDED', { exact: true }).waitFor({ state: 'visible', timeout: 8000 })
  const dockText = await dock.innerText()
  assert(dockText.includes('Run #'), 'Expected debug dock to show run tree id')
  assert(dockText.includes('SUCCEEDED'), 'Expected debug dock detail to show successful status')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow debug dock run e2e')
} finally {
  await browser.close()
}
