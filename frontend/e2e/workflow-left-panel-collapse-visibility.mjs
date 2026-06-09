import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function canvasMetrics(page) {
  return page.evaluate(() => {
    const stage = document.querySelector('.canvas-stage-shell')?.getBoundingClientRect()
    const flow = document.querySelector('.coze-flow')?.getBoundingClientRect()
    const nodes = Array.from(document.querySelectorAll('.vue-flow__node')).map((node) => {
      const rect = node.getBoundingClientRect()
      return { id: node.getAttribute('data-id'), width: rect.width, height: rect.height, left: rect.left, top: rect.top }
    })
    const edges = Array.from(document.querySelectorAll('.vue-flow__edge')).map((edge) => {
      const rect = edge.getBoundingClientRect()
      return { width: rect.width, height: rect.height }
    })
    return {
      stage: stage ? { width: stage.width, height: stage.height, left: stage.left } : null,
      flow: flow ? { width: flow.width, height: flow.height } : null,
      nodes,
      edges,
    }
  })
}

function assertCanvasAlive(metrics, label, minEdges) {
  assert(metrics.stage?.width > 600 && metrics.stage?.height > 500, `${label} stage should stay visible: ${JSON.stringify(metrics)}`)
  assert(metrics.flow?.width > 600 && metrics.flow?.height > 500, `${label} flow should stay visible: ${JSON.stringify(metrics)}`)
  assert(metrics.nodes.length >= 2, `${label} should keep start/end nodes: ${JSON.stringify(metrics)}`)
  for (const node of metrics.nodes) {
    assert(node.width > 80 && node.height > 40, `${label} node should keep measurable layout: ${JSON.stringify(node)}`)
  }
  assert(metrics.edges.length >= minEdges, `${label} should keep expected edges: ${JSON.stringify(metrics)}`)
}

async function verifyLeftPanelCollapse(page, path, expectedTitle, minEdges, captureCollapsed = false) {
  await page.goto(`${baseUrl}${path}`, { waitUntil: 'networkidle' })
  const panel = page.getByTestId('canvas-resource-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert((await panel.innerText()).includes(expectedTitle), `${path} should render ${expectedTitle} left panel`)

  const before = await canvasMetrics(page)
  assertCanvasAlive(before, `${path} before collapse`, minEdges)

  await panel.getByRole('button', { name: '折叠侧栏', exact: true }).click()
  await page.getByRole('button', { name: '展开侧栏', exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.getByTestId('canvas-resource-panel').count() === 0, `${path} should hide resource panel after collapse`)
  await page.waitForTimeout(260)

  const collapsed = await canvasMetrics(page)
  assertCanvasAlive(collapsed, `${path} collapsed`, minEdges)
  assert(
    collapsed.stage.width > before.stage.width + 100,
    `${path} collapsed canvas should reclaim left-panel width: before=${JSON.stringify(before.stage)} collapsed=${JSON.stringify(collapsed.stage)}`,
  )
  if (captureCollapsed && screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  await page.getByRole('button', { name: '展开侧栏', exact: true }).click()
  await page.getByTestId('canvas-resource-panel').waitFor({ state: 'visible', timeout: 5000 })
  await page.waitForTimeout(260)
  const expanded = await canvasMetrics(page)
  assertCanvasAlive(expanded, `${path} expanded`, minEdges)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await verifyLeftPanelCollapse(page, '/chatflows/create', '对话设置', 1, true)
  await verifyLeftPanelCollapse(page, '/workflows/create', '画布概览', 0)

  console.log('PASS workflow/chatflow left panel collapse visibility e2e')
} finally {
  await browser.close()
}
