import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_FRONTEND_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''
const widths = [1280, 1920]

const browser = await chromium.launch({ headless: true })
const failures = []
const results = []

async function snapshot(page, selector) {
  return page.evaluate((targetSelector) => {
    const rootStyle = getComputedStyle(document.documentElement)
    const target = document.querySelector(targetSelector)?.getBoundingClientRect()
    return {
      ready: document.documentElement.dataset.hifyUiScale,
      rootFont: Number.parseFloat(rootStyle.fontSize),
      scale: rootStyle.getPropertyValue('--hify-scale').trim(),
      targetWidth: target?.width ?? 0,
      targetHeight: target?.height ?? 0,
      bodyTextLength: document.body.innerText.trim().length,
      overflowX: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
    }
  }, selector)
}

for (const width of widths) {
  const expectedRoot = width === 1280 ? 14 : 16

  const workbench = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 })
  try {
    await workbench.goto(`${baseUrl}/agents/new`, { waitUntil: 'networkidle' })
    await workbench.waitForSelector('[data-testid="agent-workbench-shell"]', { timeout: 20000 })
    await workbench.waitForSelector('[data-testid="agent-workbench-preview"]', { timeout: 10000 })
    const data = await snapshot(workbench, '[data-testid="agent-workbench-shell"]')
    const preview = await workbench.locator('[data-testid="agent-workbench-preview"]').boundingBox()
    const ok = data.ready === 'ready'
      && Math.abs(data.rootFont - expectedRoot) < 0.2
      && data.targetWidth > 0
      && data.targetHeight > 0
      && data.bodyTextLength > 0
      && data.overflowX === 0
      && (preview?.width ?? 0) > 0
    if (!ok) failures.push({ route: '/agents/new', width, data, preview })
    results.push({ route: '/agents/new', width, ...data, previewWidth: preview?.width ?? 0 })
    if (screenshotDir && width === 1280) await workbench.screenshot({ path: `${screenshotDir}/agents-new-1280.png`, fullPage: true })
  } catch (error) {
    failures.push({ route: '/agents/new', width, error: error instanceof Error ? error.message : String(error) })
  } finally {
    await workbench.close()
  }

  const chat = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 })
  try {
    await chat.goto(`${baseUrl}/chat`, { waitUntil: 'networkidle' })
    await chat.waitForSelector('.chat-layout', { timeout: 20000 })
    await chat.getByRole('button', { name: /新建/ }).click()
    await chat.waitForSelector('.el-dialog', { state: 'visible', timeout: 10000 })
    const data = await snapshot(chat, '.chat-layout')
    const dialog = await chat.locator('.el-dialog').boundingBox()
    const ok = data.ready === 'ready'
      && Math.abs(data.rootFont - expectedRoot) < 0.2
      && data.targetWidth > 0
      && data.targetHeight > 0
      && data.bodyTextLength > 0
      && data.overflowX === 0
      && (dialog?.width ?? 0) > 0
    if (!ok) failures.push({ route: '/chat', width, data, dialog })
    results.push({ route: '/chat', width, ...data, dialogWidth: dialog?.width ?? 0 })
    if (screenshotDir && width === 1280) await chat.screenshot({ path: `${screenshotDir}/chat-dialog-1280.png`, fullPage: true })
  } catch (error) {
    failures.push({ route: '/chat', width, error: error instanceof Error ? error.message : String(error) })
  } finally {
    await chat.close()
  }
}

await browser.close()

console.log(JSON.stringify({ baseUrl, results, failures }, null, 2))

if (failures.length > 0) {
  process.exit(1)
}
