import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function paletteSummary(palette, groupSelector = '.node-palette-group') {
  return palette.evaluate((element, selector) => {
    const groups = Array.from(element.querySelectorAll(selector)).map((group) => ({
      title: group.querySelector('strong')?.textContent?.trim() || '',
      labels: Array.from(group.querySelectorAll('button')).map((button) => button.getAttribute('aria-label') || button.textContent?.trim() || ''),
      gridColumns: getComputedStyle(group.querySelector('.node-palette-grid, .edge-node-palette-grid') || group.querySelector('div') || group)
        .gridTemplateColumns
        .split(' ')
        .filter(Boolean).length,
    }))
    const labels = groups.flatMap((group) => group.labels)
    return {
      groups,
      duplicateLabels: labels.filter((label, index) => labels.indexOf(label) !== index),
      smallCount: element.querySelectorAll('small').length,
    }
  }, groupSelector)
}

async function paletteMetrics(palette) {
  return palette.evaluate((element) => {
    const root = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
    const rect = element.getBoundingClientRect()
    const button = element.querySelector('button')
    const buttonRect = button?.getBoundingClientRect()
    const buttonStyle = button ? getComputedStyle(button) : null
    const inputWrapper = element.querySelector('.el-input__wrapper')
    const inputRect = inputWrapper?.getBoundingClientRect()
    return {
      widthRem: rect.width / root,
      buttonHeightRem: buttonRect ? buttonRect.height / root : 0,
      buttonFontRem: buttonStyle ? Number.parseFloat(buttonStyle.fontSize) / root : 0,
      inputHeightRem: inputRect ? inputRect.height / root : 0,
    }
  })
}

function assertCozePalette(summary, label) {
  const titles = summary.groups.map((group) => group.title)
  assert(JSON.stringify(titles) === JSON.stringify(['资源', '业务逻辑', '输入&输出', '知识库']), `${label} group order mismatch: ${JSON.stringify(summary)}`)
  assert(summary.smallCount === 0, `${label} should not render node descriptions: ${JSON.stringify(summary)}`)
  assert(summary.duplicateLabels.length === 0, `${label} should not duplicate node entries: ${JSON.stringify(summary)}`)
  assert(summary.groups[0].labels.slice(0, 3).join('|') === '大模型|插件|工作流', `${label} resource group should start with Coze resource entries: ${JSON.stringify(summary)}`)
  assert(summary.groups[1].labels.includes('选择器'), `${label} business logic should expose 选择器: ${JSON.stringify(summary)}`)
  assert(summary.groups[2].labels.includes('消息') && summary.groups[2].labels.includes('问题'), `${label} input/output group should expose chatflow entries: ${JSON.stringify(summary)}`)
  assert(summary.groups[3].labels.includes('知识库检索'), `${label} knowledge group should expose 知识库检索: ${JSON.stringify(summary)}`)
  for (const group of summary.groups) {
    assert(group.gridColumns >= 2, `${label} group ${group.title} should use a two-column compact grid: ${JSON.stringify(summary)}`)
  }
}

function assertCompactPalette(metrics, label) {
  assert(metrics.widthRem <= 20, `${label} width should be compact, got ${JSON.stringify(metrics)}`)
  assert(metrics.buttonHeightRem <= 2.4, `${label} row height should be compact, got ${JSON.stringify(metrics)}`)
  assert(metrics.buttonFontRem <= 0.875, `${label} font should be one step smaller, got ${JSON.stringify(metrics)}`)
  assert(metrics.inputHeightRem <= 2.4, `${label} search input should be compact, got ${JSON.stringify(metrics)}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })

  const toolbar = page.getByTestId('canvas-bottom-toolbar')
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })
  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  const bottomPalette = page.getByTestId('bottom-node-palette')
  await bottomPalette.waitFor({ state: 'visible', timeout: 5000 })
  assertCozePalette(await paletteSummary(bottomPalette), 'bottom palette')
  const bottomMetrics = await paletteMetrics(bottomPalette)
  assertCompactPalette(bottomMetrics, 'bottom palette')

  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  const edge = page.locator('.vue-flow__edge').first()
  await edge.waitFor({ state: 'visible', timeout: 5000 })
  await edge.locator('.vue-flow__edge-interaction').hover({ force: true })
  const insertButton = page.getByTestId('edge-insert-button')
  await insertButton.waitFor({ state: 'visible', timeout: 5000 })
  await insertButton.click()
  const edgePalette = page.getByTestId('edge-insert-palette')
  await edgePalette.waitFor({ state: 'visible', timeout: 5000 })
  assertCozePalette(await paletteSummary(edgePalette, '.edge-insert-palette-group'), 'edge insert palette')
  const edgeMetrics = await paletteMetrics(edgePalette)
  assertCompactPalette(edgeMetrics, 'edge insert palette')
  assert(Math.abs(bottomMetrics.widthRem - edgeMetrics.widthRem) <= 1, `palette widths should match across entrypoints: ${JSON.stringify({ bottomMetrics, edgeMetrics })}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow add-node palette coze')
} finally {
  await browser.close()
}
