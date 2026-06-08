import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function rect(locator) {
  return locator.evaluate((element) => {
    const box = element.getBoundingClientRect()
    return { top: box.top, left: box.left, width: box.width, height: box.height }
  })
}

async function cssPosition(locator) {
  return locator.evaluate((element) => getComputedStyle(element).position)
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
  const modelSection = panel.getByTestId('llm-model-section')
  const skillSection = panel.getByTestId('llm-resource-section')

  const skillBeforeModel = await rect(skillSection)
  await modelSection.getByTestId('llm-model-display').click()
  const modelPicker = modelSection.getByTestId('llm-model-selector')
  await modelPicker.waitFor({ state: 'visible', timeout: 5000 })
  const skillAfterModel = await rect(skillSection)
  assert(
    Math.abs(skillAfterModel.top - skillBeforeModel.top) <= 1,
    `Model picker must not reflow skill section: before=${JSON.stringify(skillBeforeModel)} after=${JSON.stringify(skillAfterModel)}`,
  )
  assert(['absolute', 'fixed'].includes(await cssPosition(modelPicker)), 'Model picker must be a floating overlay')

  await modelSection.getByTestId('llm-model-display').click()
  await modelPicker.waitFor({ state: 'hidden', timeout: 5000 })
  const skillBeforeSkill = await rect(skillSection)
  await skillSection.getByRole('button', { name: '添加资源', exact: true }).click()
  const skillPicker = skillSection.getByTestId('llm-skill-picker')
  await skillPicker.waitFor({ state: 'visible', timeout: 5000 })
  const skillAfterSkill = await rect(skillSection)
  assert(
    Math.abs(skillAfterSkill.height - skillBeforeSkill.height) <= 1,
    `Skill picker must not grow its section: before=${JSON.stringify(skillBeforeSkill)} after=${JSON.stringify(skillAfterSkill)}`,
  )
  assert(['absolute', 'fixed'].includes(await cssPosition(skillPicker)), 'Skill picker must be a floating overlay')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow floating selectors e2e')
} finally {
  await browser.close()
}

