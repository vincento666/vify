import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await assertBodyIncludes(page, '评测')
  await assertBodyIncludes(page, '实验')
  await assertBodyIncludes(page, '评测集')
  await assertBodyIncludes(page, '评估器')
  await assertBodyIncludes(page, '运行记录')
  await assertBodyIncludes(page, '对比分析')
  await page.getByTestId('create-experiment').waitFor({ state: 'visible', timeout: 5000 })
  const emptyStateCount = await page.locator('.empty-panel', { hasText: '先跑一次目标实验' }).count()
  const experimentCardCount = await page.locator('.experiment-card').count()
  assert(
    emptyStateCount === 1 || experimentCardCount > 0,
    'Expected experiments tab to show either the empty-state guidance or existing experiment cards',
  )

  const compareTab = page.getByRole('tab', { name: '对比分析' })
  await compareTab.waitFor({ state: 'visible', timeout: 5000 })
  await compareTab.click()
  await page.getByTestId('compare-base-run').waitFor({ state: 'visible', timeout: 5000 })
  await page.getByTestId('compare-candidate-run').waitFor({ state: 'visible', timeout: 5000 })
  await page.getByTestId('run-compare').waitFor({ state: 'visible', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  await page.getByRole('tab', { name: '评测集' }).click()
  await assertBodyIncludes(page, '维护可复用的回归用例')

  await page.getByRole('tab', { name: '评估器' }).click()
  await assertBodyIncludes(page, '定义可解释的打分规则')

  await page.getByRole('tab', { name: '运行记录' }).click()
  await page.getByRole('heading', { name: '运行记录' }).waitFor({ state: 'visible', timeout: 5000 })

  console.log('PASS evaluation workbench shell e2e')
} finally {
  await browser.close()
}
