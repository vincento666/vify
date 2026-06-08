import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  const toolbar = page.locator('[data-testid="canvas-bottom-toolbar"]')
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })

  await toolbar.locator('.toolbar-zoom').click()
  let menu = page.locator('[data-testid="canvas-zoom-menu"]')
  await menu.waitFor({ state: 'visible', timeout: 5000 })
  await menu.getByRole('menuitem', { name: '100%', exact: true }).click()
  await toolbar.getByRole('button', { name: '缩放 100%', exact: true }).waitFor({ state: 'visible', timeout: 5000 })

  await toolbar.getByRole('button', { name: '放大显示比例', exact: true }).click()
  await toolbar.getByRole('button', { name: '放大显示比例', exact: true }).click()
  await toolbar.getByRole('button', { name: '缩放 150%', exact: true }).waitFor({ state: 'visible', timeout: 5000 })

  await toolbar.getByRole('button', { name: '缩小显示比例', exact: true }).click()
  await toolbar.getByRole('button', { name: '缩放 125%', exact: true }).waitFor({ state: 'visible', timeout: 5000 })

  await toolbar.getByRole('button', { name: '缩放 125%', exact: true }).click()
  menu = page.locator('[data-testid="canvas-zoom-menu"]')
  await menu.waitFor({ state: 'visible', timeout: 5000 })
  for (const label of ['25%', '50%', '75%', '100%', '125%', '150%']) {
    assert(await menu.getByRole('menuitem', { name: label, exact: true }).count() === 1, `Expected zoom preset ${label}`)
  }
  await menu.getByRole('menuitem', { name: '50%', exact: true }).click()
  await toolbar.getByRole('button', { name: '缩放 50%', exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  await menu.waitFor({ state: 'hidden', timeout: 5000 })

  await toolbar.getByRole('button', { name: '鼠标模式', exact: true }).click()
  await toolbar.getByRole('button', { name: '触控板模式', exact: true }).waitFor({ state: 'visible', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow toolbar zoom e2e')
} finally {
  await browser.close()
}
