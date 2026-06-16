import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const demoHostContext = {
  apiBaseUrl: '/api',
  actorId: 'mvp-demo-operator',
  actorName: 'MVP Demo Operator',
  tenantId: 'mvp-demo-tenant',
  orgId: 'mvp-demo-org',
  roles: ['customer_service_operator'],
  permissions: ['customer_assistant:read', 'customer_assistant:operate'],
  source: 'mvp-demo-shell',
  locale: 'zh-CN',
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.addInitScript((hostContext) => {
    globalThis.__HIFY_HOST__ = hostContext
  }, demoHostContext)

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  const storyStrip = page.getByTestId('customer-assistant-demo-stories')
  await storyStrip.getByRole('button', { name: /退票 \+ 行李额并行/ }).click()
  await page.getByText(/Session #/).waitFor({ state: 'visible', timeout: 10000 })

  await page.getByLabel('坐席侧内部追问').fill('退票和行李额可以并行处理吗？')
  await page.getByRole('button', { name: /追问助手/ }).click()
  await page
    .getByTestId('operator-recommendation-panel')
    .getByText(/执行写操作前分别确认/)
    .waitFor({ state: 'visible', timeout: 10000 })

  const evidencePanel = page.getByTestId('operator-advisory-evidence-panel')
  await evidencePanel
    .locator('.advisory-evidence-row')
    .filter({ hasText: 'SOP 2' })
    .last()
    .waitFor({ state: 'visible', timeout: 10000 })
  const evidenceText = await evidencePanel.innerText()
  assert(evidenceText.includes('任务 2'), `Expected task count evidence, got: ${evidenceText}`)
  assert(evidenceText.includes('SOP 2'), `Expected SOP evidence count, got: ${evidenceText}`)
  assert(evidenceText.includes('知识 1'), `Expected knowledge snippet count, got: ${evidenceText}`)
  assert(!evidenceText.includes('13800138000'), `Expected phone redaction in evidence panel, got: ${evidenceText}`)
  assert(!evidenceText.includes('TK-100'), `Expected order redaction in evidence panel, got: ${evidenceText}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant advisory evidence e2e')
} finally {
  await browser.close()
}
