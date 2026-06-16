import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '实验', exact: true }).click()
  await page.getByTestId('create-experiment').click()
  const stepper = page.getByTestId('experiment-stepper')
  await stepper.waitFor({ state: 'visible', timeout: 10000 })

  const steps = stepper.locator('.el-steps')
  for (const text of ['基础信息', '评测集', '评测对象', '评估器', '确认']) {
    await steps.getByText(text, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  }

  await page.getByTestId('experiment-step-position').getByText('1 / 5', { exact: true }).waitFor({ state: 'visible' })
  await page.getByTestId('experiment-step-next').click()
  await page.getByTestId('experiment-step-position').getByText('2 / 5', { exact: true }).waitFor({ state: 'visible' })
  await page.getByTestId('experiment-step-next').click()
  await page.getByTestId('experiment-step-position').getByText('3 / 5', { exact: true }).waitFor({ state: 'visible' })
  await page.getByTestId('experiment-step-prev').click()
  await page.getByTestId('experiment-step-position').getByText('2 / 5', { exact: true }).waitFor({ state: 'visible' })
  await page.getByTestId('experiment-step-cancel').click()
  await stepper.waitFor({ state: 'hidden', timeout: 10000 })
  assert(await page.getByTestId('create-experiment').isVisible(), 'Expected experiments list toolbar after returning')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log('PASS experiment stepper e2e')
} finally {
  await browser.close()
}
