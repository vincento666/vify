import { chromium } from 'playwright'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const __dirname = dirname(fileURLToPath(import.meta.url))
const csvPath = join(__dirname, 'fixtures', 'eval-cases.csv')
const evalSetName = `E2E CSV Eval Set ${Date.now()}`

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
}

const browser = await chromium.launch()
const context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1440, height: 900 } })
const page = await context.newPage()

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '评测集' }).click()
  await page.getByTestId('create-eval-set').click()
  await page.getByPlaceholder('请输入评测集名称').fill(evalSetName)
  await page.getByTestId('save-eval-set').click()
  await page.locator('h2', { hasText: evalSetName }).waitFor({ state: 'visible', timeout: 5000 })
  await page.getByTestId('csv-import-input').setInputFiles(csvPath)
  await page.getByText('shipping status', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  await assertBodyIncludes(page, 'shipping status')
  await page.getByRole('button', { name: '返回评测集' }).click()
  await page.locator('.eval-set-card').filter({ hasText: evalSetName }).getByText('2 条用例', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })

  await page.getByRole('tab', { name: '运行记录' }).click()
  await page.getByRole('button', { name: '查看报告' }).first().click()
  await page.getByText('目标输出').waitFor({ state: 'visible', timeout: 10000 })
  const downloadPromise = page.waitForEvent('download')
  await page.getByTestId('export-run-csv').click()
  const download = await downloadPromise
  assert((await download.suggestedFilename()).endsWith('.csv'), 'Expected CSV download filename')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS evaluation CSV import/export e2e')
} finally {
  await browser.close()
}
