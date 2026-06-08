import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function waitForPanelSettled(page) {
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  }))
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'load' })
  await page.getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByTestId('llm-model-section').waitFor({ state: 'visible', timeout: 5000 })
  await waitForPanelSettled(page)
  await panel.getByRole('button', { name: '模型设置', exact: true }).click({ force: true })
  const parameterPanel = panel.getByTestId('llm-model-parameter-panel')
  await parameterPanel.waitFor({ state: 'visible', timeout: 5000 })

  assert(await parameterPanel.getByTestId('model-parameter-dial').count() === 0, 'Model parameters must not render circular dials')
  const sliders = parameterPanel.getByTestId('model-parameter-slider')
  assert(await sliders.count() >= 5, 'Numeric model parameters should render long slider tracks')

  const temperature = parameterPanel.getByTestId('model-parameter-temperature')
  const slider = temperature.getByTestId('model-parameter-slider')
  const numberInput = temperature.getByTestId('model-parameter-number-input')
  const sliderBox = await slider.boundingBox()
  const inputBox = await numberInput.boundingBox()
  assert(sliderBox && inputBox, 'Expected slider and number input geometry')
  assert(sliderBox.width > 140, `Slider track should be long, got ${sliderBox.width}`)
  assert(inputBox.x > sliderBox.x + sliderBox.width - 2, `Number input should sit to the right of the slider, slider=${JSON.stringify(sliderBox)} input=${JSON.stringify(inputBox)}`)
  assert(await slider.getAttribute('type') === 'range', 'Slider should be a native range input with a draggable dot thumb')

  const spinInput = numberInput.locator('input')
  await spinInput.fill('1.20')
  await spinInput.press('Enter')
  assert(Number(await spinInput.inputValue()) === 1.2, 'Number input should remain directly editable')
  const increaseButton = numberInput.locator('.el-input-number__increase')
  assert(await increaseButton.count() === 1, 'Number input should expose an increase micro-adjust control')
  await increaseButton.click()
  assert(Number(await spinInput.inputValue()) > 1.2, 'Increase control should micro-adjust the value')

  const maxTokens = parameterPanel.getByTestId('model-parameter-maxTokens')
  const maxTokensNumberInput = maxTokens.getByTestId('model-parameter-number-input')
  const density = await maxTokensNumberInput.evaluate((element) => {
    const input = element.querySelector('input')
    const increase = element.querySelector('.el-input-number__increase')
    const decrease = element.querySelector('.el-input-number__decrease')
    const wrapper = element.querySelector('.el-input__wrapper')
    const inputStyle = input ? window.getComputedStyle(input) : null
    const wrapperStyle = wrapper ? window.getComputedStyle(wrapper) : null
    return {
      increaseWidth: increase?.getBoundingClientRect().width ?? 0,
      decreaseWidth: decrease?.getBoundingClientRect().width ?? 0,
      inputPaddingLeft: inputStyle ? Number.parseFloat(inputStyle.paddingLeft) : 0,
      inputPaddingRight: inputStyle ? Number.parseFloat(inputStyle.paddingRight) : 0,
      wrapperPaddingLeft: wrapperStyle ? Number.parseFloat(wrapperStyle.paddingLeft) : 0,
      wrapperPaddingRight: wrapperStyle ? Number.parseFloat(wrapperStyle.paddingRight) : 0,
    }
  })
  assert(density.increaseWidth <= 20 && density.decreaseWidth <= 20, `Stepper buttons should be narrow, got ${JSON.stringify(density)}`)
  assert(density.inputPaddingLeft <= 4 && density.inputPaddingRight <= 4, `Input internal padding should be compact, got ${JSON.stringify(density)}`)
  assert(density.wrapperPaddingLeft <= 6 && density.wrapperPaddingRight <= 24, `Input wrapper padding should leave enough room for values, got ${JSON.stringify(density)}`)
  const maxTokensSpinInput = maxTokensNumberInput.locator('input')
  await maxTokensSpinInput.fill('200000')
  await maxTokensSpinInput.press('Enter')
  const visibility = await maxTokensSpinInput.evaluate((input) => ({
    value: input.value,
    clientWidth: input.clientWidth,
    scrollWidth: input.scrollWidth,
  }))
  assert(visibility.value === '200000', `Max token value should be editable, got ${JSON.stringify(visibility)}`)
  assert(visibility.scrollWidth <= visibility.clientWidth + 1, `Max token value should fit without clipping, got ${JSON.stringify(visibility)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow model parameter slider 028')
} finally {
  await browser.close()
}
