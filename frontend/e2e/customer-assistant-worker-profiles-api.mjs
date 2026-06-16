import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1024, height: 768 } })

try {
  await page.goto(`${baseUrl}/api/v1/customer-assistant/worker-profiles`, { waitUntil: 'networkidle' })
  const text = await page.locator('body').innerText()
  const payload = JSON.parse(text)
  assert(payload.code === 200, `Expected success envelope, got ${payload.code}`)
  assert(payload.data.total >= 3, `Expected default worker profiles, got ${payload.data.total}`)
  const refund = payload.data.list.find((profile) => profile.taskKey === 'refund_ticket')
  assert(refund, 'Expected refund_ticket profile')
  assert(refund.workerType === 'chatflow_sop', `Unexpected refund worker type: ${refund.workerType}`)
  assert(refund.riskPolicyRef === 'manual_confirm', `Unexpected risk policy: ${refund.riskPolicyRef}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant worker profiles api e2e')
} finally {
  await browser.close()
}
