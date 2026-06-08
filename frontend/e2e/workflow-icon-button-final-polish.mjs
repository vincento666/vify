import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function buttonMetrics(locator, label) {
  return locator.evaluate((element) => {
    const style = getComputedStyle(element)
    const box = element.getBoundingClientRect()
    const svg = element.querySelector('svg')
    const svgStyle = svg ? getComputedStyle(svg) : null
    return {
      label: element.getAttribute('aria-label') || label,
      width: Math.round(box.width),
      height: Math.round(box.height),
      borderColor: style.borderColor,
      backgroundColor: style.backgroundColor,
      borderRadius: style.borderRadius,
      svgCount: element.querySelectorAll('svg').length,
      svgStrokeWidth: svgStyle?.strokeWidth || '',
      text: element.textContent?.trim() || '',
    }
  })
}

function isTransparent(color) {
  return color === 'rgba(0, 0, 0, 0)' || color === 'transparent'
}

function assertLightIconButton(metrics) {
  assert(metrics.svgCount >= 1, `Expected icon button svg: ${JSON.stringify(metrics)}`)
  assert(!isTransparent(metrics.borderColor), `Expected visible border: ${JSON.stringify(metrics)}`)
  assert(!isTransparent(metrics.backgroundColor), `Expected visible background: ${JSON.stringify(metrics)}`)
  assert(metrics.height >= 28 && metrics.height <= 36, `Expected compact icon height: ${JSON.stringify(metrics)}`)
  assert(parseFloat(metrics.svgStrokeWidth || '0') <= 2, `Expected light svg stroke: ${JSON.stringify(metrics)}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })

  const toolbar = page.getByTestId('canvas-bottom-toolbar')
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })
  for (const label of ['缩小显示比例', '放大显示比例', '自动布局', '鼠标模式', '调试工具']) {
    assertLightIconButton(await buttonMetrics(toolbar.getByRole('button', { name: label, exact: true }), label))
  }

  await page.locator('.vue-flow__node[data-id="end"]').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assertLightIconButton(await buttonMetrics(panel.getByRole('button', { name: '关闭配置', exact: true }), '关闭配置'))

  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  assertLightIconButton(await buttonMetrics(page.getByRole('button', { name: '模型设置', exact: true }), '模型设置'))
  assertLightIconButton(await buttonMetrics(page.getByRole('button', { name: '添加资源', exact: true }), '添加资源'))
  assertLightIconButton(await buttonMetrics(page.getByTestId('config-section-输入').getByRole('button', { name: '添加输入变量', exact: true }), '添加输入变量'))

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow icon button final polish')
} finally {
  await browser.close()
}
