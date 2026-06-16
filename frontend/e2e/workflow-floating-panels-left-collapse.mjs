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

async function createWorkflow(page) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `Floating Panels Left Collapse ${Date.now()}`,
        description: 'debug dock and node test drawer should push layout without zooming or hiding the toolbar',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 160 } } } },
          {
            nodeKey: 'llm',
            type: 'LLM',
            name: '大模型',
            config: {
              inputParameters: [{ name: 'input', type: 'string', valueMode: 'reference', value: '{{start.USER_INPUT}}' }],
              outputVariable: 'answer',
              ui: { position: { x: 520, y: 160 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { output: '{{llm.answer}}', ui: { position: { x: 900, y: 160 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm', condition: null },
          { sourceNodeKey: 'llm', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create workflow',
  )
}

async function geometry(page) {
  return page.evaluate(() => {
    const rect = (selector) => {
      const element = document.querySelector(selector)
      if (!element) return null
      const box = element.getBoundingClientRect()
      return {
        left: box.left,
        right: box.right,
        top: box.top,
        bottom: box.bottom,
        width: box.width,
        height: box.height,
      }
    }
    return {
      viewportWidth: window.innerWidth,
      resource: rect('[data-testid="canvas-resource-panel"]'),
      resourceToggle: rect('.resource-panel-toggle'),
      toolbar: rect('[data-testid="canvas-bottom-toolbar"]'),
      debugDock: rect('[data-testid="workflow-debug-dock"]'),
      drawer: rect('[data-testid="node-test-drawer"]'),
      config: rect('[data-testid="node-config-panel"]'),
    }
  })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 980, height: 880 } })

try {
  const workflow = await createWorkflow(page)
  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })

  const node = page.locator('.vue-flow__node[data-id="llm"]')
  await node.waitFor({ state: 'visible', timeout: 10000 })
  await node.click()

  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.getByTestId('canvas-resource-panel').isVisible(), 'Expected the left overview panel to start expanded')

  await panel.getByRole('button', { name: '试运行当前节点', exact: true }).click()
  const drawer = page.getByTestId('node-test-drawer')
  await drawer.waitFor({ state: 'visible', timeout: 5000 })
  await drawer.getByRole('button', { name: '查看日志', exact: true }).click()
  await page.getByTestId('workflow-debug-dock').waitFor({ state: 'visible', timeout: 5000 })

  await panel.getByRole('button', { name: '关闭配置', exact: true }).click({ force: true })
  await panel.waitFor({ state: 'hidden', timeout: 5000 })
  await page.waitForTimeout(260)

  const boxes = await geometry(page)
  assert(boxes.resource, `Expected left overview panel to stay expanded instead of auto-collapsing, got ${JSON.stringify(boxes)}`)
  assert(boxes.debugDock && boxes.drawer, `Expected debug dock and node test drawer, got ${JSON.stringify(boxes)}`)
  assert(boxes.debugDock.width >= 520, `Expected debug dock to recover useful width, got ${JSON.stringify(boxes)}`)
  assert(boxes.debugDock.right <= boxes.drawer.left - 8, `Expected debug dock not to overlap node test drawer, got ${JSON.stringify(boxes)}`)
  assert(boxes.toolbar && boxes.toolbar.left >= 8, `Expected toolbar to stay inside viewport, got ${JSON.stringify(boxes)}`)
  const layer = await page.evaluate(() => {
    const toolbar = document.querySelector('[data-testid="canvas-bottom-toolbar"]')
    const toolbarBox = toolbar?.getBoundingClientRect()
    const dock = document.querySelector('[data-testid="workflow-debug-dock"]')
    if (!toolbarBox) return { topElementTestId: '', toolbarZ: 0, dockZ: 0 }
    const centerX = toolbarBox.left + toolbarBox.width / 2
    const centerY = toolbarBox.top + toolbarBox.height / 2
    const topElement = document.elementFromPoint(centerX, centerY)
    const zIndex = (element) => Number.parseInt(window.getComputedStyle(element).zIndex || '0', 10) || 0
    return {
      topElementTestId: topElement?.closest('[data-testid]')?.getAttribute('data-testid') || '',
      toolbarZ: toolbar ? zIndex(toolbar) : 0,
      dockZ: dock ? zIndex(dock) : 0,
    }
  })
  assert(layer.topElementTestId === 'canvas-bottom-toolbar', `Expected toolbar to be the top hit target, got ${JSON.stringify(layer)}`)
  assert(layer.toolbarZ > layer.dockZ, `Expected toolbar z-index above debug dock, got ${JSON.stringify(layer)}`)

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })
  console.log('PASS workflow floating panels left collapse e2e')
} finally {
  await browser.close()
}
