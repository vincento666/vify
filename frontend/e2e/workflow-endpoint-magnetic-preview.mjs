import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function centerOf(locator) {
  const box = await locator.boundingBox()
  assert(box, 'Expected element bounding box')
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })

  const sourcePort = page.locator('.vue-flow__node[data-id="start"] .source-port').first()
  const targetPort = page.locator('.vue-flow__node[data-id="end"] .target-port').first()
  await sourcePort.waitFor({ state: 'visible', timeout: 5000 })
  await targetPort.waitFor({ state: 'visible', timeout: 5000 })

  const source = await centerOf(sourcePort)
  const target = await centerOf(targetPort)
  const magneticPoint = { x: target.x - 16, y: target.y }

  await page.mouse.move(source.x, source.y)
  await page.mouse.down()
  await page.mouse.move((source.x + target.x) / 2, (source.y + target.y) / 2, { steps: 8 })
  await page.mouse.move(magneticPoint.x, magneticPoint.y, { steps: 8 })
  await page.waitForTimeout(180)

  const previewCount = await page.locator('.vue-flow__node[data-id="end"] .target-port.connection-preview').count()
  assert(previewCount === 1, 'Expected target endpoint to enter connection-preview inside magnetic radius')

  const previewMetrics = await targetPort.evaluate((element) => {
    const after = getComputedStyle(element, '::after')
    const root = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16
    const match = after.transform.match(/^matrix\(([^,]+),\s*([^,]+),/)
    const scale = match ? Math.hypot(Number.parseFloat(match[1]), Number.parseFloat(match[2])) : 1
    return {
      transform: after.transform,
      scale,
      widthRem: Number.parseFloat(after.width) / root,
      heightRem: Number.parseFloat(after.height) / root,
    }
  })
  assert(previewMetrics.scale > 1.05, `Expected preview endpoint dot to scale up, got ${JSON.stringify(previewMetrics)}`)

  await page.mouse.up()
  await page.waitForTimeout(180)
  await page.locator('.vue-flow__edge').waitFor({ state: 'visible', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow endpoint magnetic preview e2e')
} finally {
  await browser.close()
}
