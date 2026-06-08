import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function controlHeights(row) {
  return row.evaluate((element) => {
    return Array.from(element.querySelectorAll('.el-input__wrapper, .el-select__wrapper, button'))
      .map((control) => Math.round(control.getBoundingClientRect().height))
      .filter((height) => height > 0)
  })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()

  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert(await panel.getByTestId('config-section-输入').count() === 1, 'Expected section title 输入')
  assert(await panel.getByTestId('config-section-输入参数').count() === 0, 'Input parameters title must be gone')

  const modelToggle = panel.getByTestId('llm-model-section').getByRole('button', { name: /模型/ }).first()
  await modelToggle.waitFor({ state: 'visible', timeout: 5000 })
  assert(await modelToggle.getAttribute('aria-expanded') === 'true', 'Model section must expose aria-expanded=true')
  await modelToggle.click()
  assert(await modelToggle.getAttribute('aria-expanded') === 'false', 'Model section must collapse')
  assert(await panel.getByTestId('llm-model-display').isVisible() === false, 'Model selector must hide when collapsed')

  const skillToggle = panel.getByTestId('llm-resource-section').getByRole('button', { name: /技能/ }).first()
  assert(await skillToggle.getAttribute('aria-expanded') === 'true', 'Skill section must expose aria-expanded=true')
  await skillToggle.click()
  assert(await skillToggle.getAttribute('aria-expanded') === 'false', 'Skill section must collapse')
  assert(await panel.locator('.resource-empty-state', { hasText: '暂未配置技能' }).isVisible() === false, 'Skill content must hide when collapsed')

  await skillToggle.click()
  await modelToggle.click()
  const inputSection = panel.getByTestId('config-section-输入')
  await inputSection.getByRole('button', { name: '添加输入变量', exact: true }).click()
  await inputSection.getByRole('button', { name: '添加输入变量', exact: true }).click()
  const rows = inputSection.getByTestId('input-parameter-row')
  const rowCount = await rows.count()
  assert(rowCount >= 2, `Expected two input rows, got ${rowCount}`)
  for (let index = 0; index < rowCount; index += 1) {
    const heights = await controlHeights(rows.nth(index))
    const max = Math.max(...heights)
    const min = Math.min(...heights)
    assert(max - min <= 2, `Input row controls must align, row ${index}: ${heights.join(',')}`)
    assert(max <= 38, `Input row must remain compact, row ${index}: ${heights.join(',')}`)
  }

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log('PASS workflow config panel polish 026')
} finally {
  await browser.close()
}
