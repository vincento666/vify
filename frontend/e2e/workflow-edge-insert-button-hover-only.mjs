import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function visibleInsertButtonCount(page) {
  return page.getByTestId('edge-insert-button').evaluateAll((buttons) =>
    buttons.filter((button) => {
      const style = window.getComputedStyle(button)
      const box = button.getBoundingClientRect()
      return style.display !== 'none' && style.visibility !== 'hidden' && box.width > 0 && box.height > 0
    }).length,
  )
}

async function edgePoint(page, fraction) {
  return page.evaluate((targetFraction) => {
    const path = document.querySelector('.vue-flow__edge-interaction')
    if (!(path instanceof SVGPathElement)) return null
    const matrix = path.getScreenCTM()
    if (!matrix) return null
    const point = path.getPointAtLength(path.getTotalLength() * targetFraction)
    const svgPoint = path.ownerSVGElement?.createSVGPoint()
    if (!svgPoint) return null
    svgPoint.x = point.x
    svgPoint.y = point.y
    const screenPoint = svgPoint.matrixTransform(matrix)
    return { x: screenPoint.x, y: screenPoint.y }
  }, fraction)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  const edge = page.locator('.vue-flow__edge').first()
  await edge.waitFor({ state: 'visible', timeout: 5000 })

  await edge.locator('.vue-flow__edge-interaction').hover({ force: true })
  await page.waitForTimeout(120)
  assert(await visibleInsertButtonCount(page) === 1, 'Hovering a line should show the insert button')

  await page.mouse.move(80, 80)
  await page.waitForTimeout(160)
  assert(await visibleInsertButtonCount(page) === 0, 'Leaving a line without selecting it should hide the insert button')

  const selectPoint = await edgePoint(page, 0.18)
  assert(selectPoint, 'Expected to resolve a non-center point on the line')
  await page.mouse.move(selectPoint.x, selectPoint.y)
  await page.waitForTimeout(120)
  await page.mouse.click(selectPoint.x, selectPoint.y)
  await page.mouse.move(80, 80)
  await page.waitForTimeout(160)
  assert(await visibleInsertButtonCount(page) === 1, 'Selecting a line should keep the insert button visible after hover ends')

  const selectedEdgeClass = await page.locator('.coze-edge-path.edge-selected').count()
  assert(selectedEdgeClass === 1, 'The line should remain selected/highlighted while its insert button is visible')
  const hoveredEdgeClass = await page.locator('.coze-edge-path.edge-hovered').count()
  assert(hoveredEdgeClass === 0, 'Selected line insert button must not rely on stale hover styling')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow edge insert button hover-only e2e')
} finally {
  await browser.close()
}
