import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/agent`, { waitUntil: 'networkidle' })
  await page.getByText('Agent 管理').waitFor({ state: 'visible', timeout: 5000 })

  const widths = await page.locator('.agent-card .el-table__header-wrapper th').evaluateAll((cells) =>
    cells.map((cell) => ({
      text: cell.textContent?.trim(),
      width: Math.round(cell.getBoundingClientRect().width),
    })),
  )
  const rowMetrics = await page.locator('.agent-card .el-table__body-wrapper tbody tr').evaluateAll((rows) =>
    rows.slice(0, 8).map((row) => ({
      height: Math.round(row.getBoundingClientRect().height),
      text: row.textContent?.replace(/\s+/g, ' ').trim(),
    })),
  )
  const modelCells = await page.locator('.agent-card .agent-model-cell').evaluateAll((cells) =>
    cells.slice(0, 8).map((cell) => ({
      height: Math.round(cell.getBoundingClientRect().height),
      text: cell.textContent?.trim(),
      scrollWidth: cell.scrollWidth,
      width: Math.round(cell.getBoundingClientRect().width),
    })),
  )
  const timeCells = await page.locator('.agent-card .agent-time-cell').evaluateAll((cells) =>
    cells.slice(0, 8).map((cell) => ({
      text: cell.textContent?.trim(),
      scrollWidth: cell.scrollWidth,
      width: Math.round(cell.getBoundingClientRect().width),
    })),
  )
  const nonNameColumns = widths.slice(1)
  assert(widths.length >= 8, `Expected Agent table columns, got ${JSON.stringify(widths)}`)
  assert(nonNameColumns.every((cell) => cell.width >= 70), `Collapsed Agent table columns: ${JSON.stringify(widths)}`)
  assert(widths.find((cell) => cell.text === '操作')?.width >= 130, `Action column too narrow: ${JSON.stringify(widths)}`)
  assert(rowMetrics.length > 0, 'Expected Agent rows for layout validation')
  assert(rowMetrics.every((row) => row.height <= 54), `Long Agent data should not expand row height: ${JSON.stringify(rowMetrics)}`)
  assert(modelCells.every((cell) => cell.height <= 22), `Model cells should stay single-line: ${JSON.stringify(modelCells)}`)
  assert(timeCells.every((cell) => !cell.text?.includes('T')), `Created time should be formatted, not raw ISO: ${JSON.stringify(timeCells)}`)
  assert(timeCells.every((cell) => (cell.text || '').length <= 16), `Created time should fit compactly: ${JSON.stringify(timeCells)}`)

  const createButton = page.getByRole('button', { name: '新增 Agent' })
  await createButton.click()
  await page.waitForURL(`${baseUrl}/agents/new`, { timeout: 5000 })
  await page.getByTestId('agent-workbench-shell').waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.locator('.el-dialog').count() === 0, 'Create entry should route to workbench, not open a list dialog')

  if (screenshotPath) {
    await page.goto(`${baseUrl}/agent`, { waitUntil: 'networkidle' })
    await page.getByText('Agent 管理').waitFor({ state: 'visible', timeout: 5000 })
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent list layout e2e')
} finally {
  await browser.close()
}
