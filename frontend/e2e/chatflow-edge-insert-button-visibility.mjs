import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function visibleInsertButtonCount(page) {
  return page.getByTestId('edge-insert-button').filter({ visible: true }).count()
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Edge Insert Visibility ${Date.now()}`,
        description: 'edge insert button hover state e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 160, y: 240 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.sys.query}}', ui: { position: { x: 760, y: 240 } } } },
        ],
        edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
      },
    }),
    'create edge visibility chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  const edge = page.locator('.vue-flow__edge').first()
  await edge.waitFor({ state: 'visible', timeout: 5000 })
  await edge.locator('.vue-flow__edge-interaction').hover({ force: true })

  const visibleButton = page.getByTestId('edge-insert-button').filter({ visible: true })
  await visibleButton.waitFor({ state: 'visible', timeout: 5000 })
  const buttonBox = await visibleButton.boundingBox()
  assert(buttonBox, 'Expected visible edge insert button box')

  await page.mouse.move(buttonBox.x + buttonBox.width / 2, buttonBox.y + buttonBox.height / 2)
  await page.mouse.move(80, 820)
  await page.waitForTimeout(180)

  assert(
    await visibleInsertButtonCount(page) === 0,
    'Expected edge insert button to hide after leaving both edge and button without selecting the edge',
  )

  await edge.locator('.vue-flow__edge-interaction').click({ force: true })
  await visibleButton.waitFor({ state: 'visible', timeout: 5000 })
  await page.mouse.move(80, 820)
  await page.waitForTimeout(180)
  assert(
    await page.locator('.coze-edge-path.edge-selected').count() === 1,
    'Expected selected edge to keep an explicit selected state',
  )
  assert(
    await page.locator('.coze-edge-path.edge-hovered').count() === 0,
    'Selected edge insert button must not rely on stale hover state after the cursor leaves',
  )
  assert(
    await visibleInsertButtonCount(page) === 1,
    'Expected selected edge to keep the insert button visible until pane click clears selection',
  )

  await page.mouse.click(1200, 820)
  await page.waitForTimeout(180)
  assert(await page.locator('.coze-edge-path.edge-selected').count() === 0, 'Expected pane click to clear selected edge state')
  assert(await page.locator('.coze-edge-path.edge-hovered').count() === 0, 'Expected pane click to clear hovered edge state')
  assert(
    await visibleInsertButtonCount(page) === 0,
    'Expected pane click to clear selected edge insert button',
  )

  await edge.locator('.vue-flow__edge-interaction').hover({ force: true })
  await visibleButton.waitFor({ state: 'visible', timeout: 5000 })
  await visibleButton.click()
  await page.getByTestId('edge-insert-palette').waitFor({ state: 'visible', timeout: 5000 })
  await visibleButton.click()
  await page.getByTestId('edge-insert-palette').waitFor({ state: 'hidden', timeout: 5000 })
  await page.mouse.move(80, 820)
  await page.waitForTimeout(180)
  assert(
    await visibleInsertButtonCount(page) === 0,
    'Expected closing the edge insert palette to also clear stale edge selection and hide the plus button',
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS chatflow edge insert button visibility e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
