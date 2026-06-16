import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function parsePx(value) {
  return Number(String(value).replace('px', ''))
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })

try {
  await page.goto(`${baseUrl}/provider`, { waitUntil: 'networkidle' })
  await page.getByText('模型提供商管理').waitFor({ state: 'visible', timeout: 5000 })

  const width1280 = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement)
    const sidebar = getComputedStyle(document.querySelector('.sidebar'))
    const tableWrap = getComputedStyle(document.querySelector('.hify-table-wrap'))
    return {
      rootFontSize: root.fontSize,
      scale: root.getPropertyValue('--hify-scale').trim(),
      sidebarWidth: sidebar.width,
      tableGap: tableWrap.gap,
    }
  })

  await page.setViewportSize({ width: 1920, height: 900 })
  await page.waitForTimeout(100)

  const width1920 = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement)
    const sidebar = getComputedStyle(document.querySelector('.sidebar'))
    const tableWrap = getComputedStyle(document.querySelector('.hify-table-wrap'))
    return {
      rootFontSize: root.fontSize,
      scale: root.getPropertyValue('--hify-scale').trim(),
      sidebarWidth: sidebar.width,
      tableGap: tableWrap.gap,
      overflowX: document.documentElement.scrollWidth - window.innerWidth,
      ready: document.documentElement.dataset.hifyUiScale,
    }
  })

  assert(width1280.rootFontSize === '14px', `Expected 1280 root 14px, got ${width1280.rootFontSize}`)
  assert(width1920.rootFontSize === '16px', `Expected 1920 root 16px, got ${width1920.rootFontSize}`)
  assert(width1280.scale === '0.8750', `Expected 1280 scale 0.8750, got ${width1280.scale}`)
  assert(width1920.scale === '1.0000', `Expected 1920 scale 1.0000, got ${width1920.scale}`)
  assert(parsePx(width1920.sidebarWidth) > parsePx(width1280.sidebarWidth), 'Expected sidebar to scale up')
  assert(parsePx(width1920.tableGap) > parsePx(width1280.tableGap), 'Expected table gap to scale up')
  assert(width1920.ready === 'ready', 'Expected hify scale dataset ready')
  assert(width1920.overflowX <= 0, `Expected no horizontal overflow, got ${width1920.overflowX}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS rem scale shell e2e')
} finally {
  await browser.close()
}
