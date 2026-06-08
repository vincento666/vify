import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })

  const panel = page.getByTestId('canvas-resource-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert((await panel.innerText()).includes('对话设置'), 'Expected chatflow left panel to render dialog settings')

  const guideSection = panel.getByTestId('chatflow-guide-question-settings')
  await guideSection.waitFor({ state: 'visible', timeout: 5000 })

  const firstQuestion = guideSection.getByLabel('引导问题 1', { exact: true })
  assert(await firstQuestion.count() === 1, 'Expected first guide question input to have a semantic label')
  assert(await firstQuestion.getAttribute('placeholder') === '输入猜你想问', 'Expected guide question placeholder to explain expected content')

  const firstDelete = guideSection.getByRole('button', { name: '删除引导问题 1', exact: true })
  assert(await firstDelete.count() === 1, 'Expected guide question delete button to have a semantic Chinese label')
  assert(await firstDelete.locator('svg').count() === 1, 'Expected guide question delete button to use a lightweight icon')

  const addButton = guideSection.getByRole('button', { name: '新增引导问题', exact: true })
  assert(await addButton.count() === 1, 'Expected a semantic add guide question button')
  assert(await addButton.locator('svg').count() === 1, 'Expected add guide question button to use an icon')
  await addButton.click()

  const addedInput = guideSection.getByLabel('引导问题 4', { exact: true })
  await addedInput.waitFor({ state: 'visible', timeout: 5000 })
  await addedInput.fill('售后进度')
  assert(await addedInput.inputValue() === '售后进度', 'Expected newly added guide question to be editable')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow left panel settings e2e')
} finally {
  await browser.close()
}
