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

  const variablePanel = panel.getByTestId('chatflow-variable-panel')
  await variablePanel.waitFor({ state: 'visible', timeout: 5000 })
  assert((await variablePanel.innerText()).includes('记忆'), 'Expected chatflow variable panel to follow the memory/settings surface')
  assert((await variablePanel.innerText()).includes('会话变量 10'), 'Expected collapsed variable summary to preserve the conversation variable count')
  assert((await variablePanel.innerText()).includes('用户变量 0'), 'Expected collapsed variable summary to preserve the user variable count')

  const runtimeToggle = variablePanel.getByRole('button', { name: /会话变量/ })
  assert(await runtimeToggle.getAttribute('aria-expanded') === 'false', 'Conversation variable group should be collapsed by default')
  assert((await runtimeToggle.innerText()).includes('10'), 'Collapsed conversation variable group should show its variable count')
  assert(await variablePanel.getByTestId('chatflow-resource-variable').count() === 0, 'Collapsed variable panel should not flood the left settings panel')
  await runtimeToggle.click()
  assert(await runtimeToggle.getAttribute('aria-expanded') === 'true', 'Conversation variable group should expand on click')
  assert(await variablePanel.getByTestId('chatflow-resource-variable').count() === 10, 'Expanded conversation group should expose all conversation variables')
  assert((await variablePanel.innerText()).includes('变量 key'), 'Expanded variable group should render a HiAgent-like key column')
  assert((await variablePanel.innerText()).includes('变量显示名'), 'Expanded variable group should render a HiAgent-like display name column')
  assert((await variablePanel.innerText()).includes('操作'), 'Expanded variable group should render a HiAgent-like action column')
  assert((await variablePanel.innerText()).includes('SYS_QUERY'), 'Expanded variable group should show system keys without flooding the collapsed panel')
  assert((await variablePanel.innerText()).includes('用于存储用户使用项目过程中需要持久化存储和读取的数据'), 'Expected user variable area to explain persistent user variables')

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
