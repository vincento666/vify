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

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Edge Interactions ${Date.now()}`,
        description: 'edge interaction e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 160, y: 240 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.sys.query}}', ui: { position: { x: 760, y: 240 } } } },
        ],
        edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
      },
    }),
    'create edge interaction chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  const edge = page.locator('.vue-flow__edge').first()
  await edge.waitFor({ state: 'visible', timeout: 5000 })
  const interaction = edge.locator('.vue-flow__edge-interaction')
  const path = edge.locator('.vue-flow__edge-path')
  const defaultStrokeWidth = Number.parseFloat(await path.evaluate((element) => getComputedStyle(element).strokeWidth))

  await interaction.hover({ force: true })
  const plusButton = page.getByTestId('edge-insert-button')
  await plusButton.waitFor({ state: 'visible', timeout: 5000 })
  await page.waitForTimeout(220)
  const hoveredStrokeWidth = Number.parseFloat(await path.evaluate((element) => getComputedStyle(element).strokeWidth))
  assert(
    Math.abs(hoveredStrokeWidth - defaultStrokeWidth) <= Math.max(0.15, defaultStrokeWidth * 0.05),
    `Expected hover edge to keep width ${defaultStrokeWidth}, got ${hoveredStrokeWidth}`,
  )

  await interaction.click({ force: true })
  await page.waitForTimeout(220)
  const selectedStrokeWidth = Number.parseFloat(await path.evaluate((element) => getComputedStyle(element).strokeWidth))
  assert(
    Math.abs(selectedStrokeWidth - defaultStrokeWidth * 1.5) <= 0.15,
    `Expected selected edge to be 1.5x default ${defaultStrokeWidth}, got ${selectedStrokeWidth}`,
  )

  await page.keyboard.press('Backspace')
  await page.waitForTimeout(150)
  assert(await page.locator('.vue-flow__edge').count() === 0, 'Expected selected edge to delete via Backspace')
  assert(await page.locator('.vue-flow__node[data-id="start"]').count() === 1, 'Expected START node to remain after edge delete')
  assert(await page.locator('.vue-flow__node[data-id="end"]').count() === 1, 'Expected END node to remain after edge delete')

  await page.reload({ waitUntil: 'networkidle' })
  const reloadedEdge = page.locator('.vue-flow__edge').first()
  await reloadedEdge.locator('.vue-flow__edge-interaction').hover({ force: true })
  const insertButton = page.getByTestId('edge-insert-button')
  await insertButton.click()
  const palette = page.getByTestId('edge-insert-palette')
  await palette.waitFor({ state: 'visible', timeout: 5000 })

  const boxes = await page.evaluate(() => {
    const buttonElement = document.querySelector('[data-testid="edge-insert-button"]')
    const panelElement = document.querySelector('[data-testid="edge-insert-palette"]')
    const button = buttonElement?.getBoundingClientRect()
    const panel = panelElement?.getBoundingClientRect()
    return {
      button: button ? { left: button.left, top: button.top, right: button.right, bottom: button.bottom, width: button.width, height: button.height } : null,
      panel: panel ? { left: panel.left, top: panel.top, right: panel.right, bottom: panel.bottom, width: panel.width, height: panel.height } : null,
      buttonZIndex: buttonElement ? Number(window.getComputedStyle(buttonElement).zIndex || 0) : 0,
      panelZIndex: panelElement ? Number(window.getComputedStyle(panelElement).zIndex || 0) : 0,
    }
  })
  assert(boxes.button && boxes.panel, `Expected edge insert button and palette boxes, got ${JSON.stringify(boxes)}`)
  const overlapX = Math.max(0, Math.min(boxes.button.right, boxes.panel.right) - Math.max(boxes.button.left, boxes.panel.left))
  const overlapY = Math.max(0, Math.min(boxes.button.bottom, boxes.panel.bottom) - Math.max(boxes.button.top, boxes.panel.top))
  assert(overlapX * overlapY === 0, `Expected edge insert palette not to overlap plus button: ${JSON.stringify(boxes)}`)
  assert(boxes.panel.left >= boxes.button.right + 4, `Expected edge insert palette to open away from plus button: ${JSON.stringify(boxes)}`)
  assert(boxes.panelZIndex > boxes.buttonZIndex, `Expected palette z-index above plus button: ${JSON.stringify(boxes)}`)

  await palette.getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.locator('.vue-flow__edge').count() === 2, 'Expected inserted node to split the original edge into two edges')
  assert(await palette.count() === 0, 'Expected edge insert palette to close after choosing a node')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow edge interactions e2e')
} finally {
  await browser.close()
}
