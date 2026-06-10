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

async function canvasMetrics(page, nodeSelector) {
  return page.evaluate((selector) => {
    const flow = document.querySelector('.coze-flow')
    const viewport = document.querySelector('.vue-flow__viewport')
    const node = document.querySelector(selector)
    const zoomLabel = document.querySelector('.toolbar-zoom')
    if (!flow || !viewport || !node) {
      throw new Error('Expected workflow canvas, viewport, and target node to be visible')
    }
    const flowRect = flow.getBoundingClientRect()
    const nodeRect = node.getBoundingClientRect()
    const transform = window.getComputedStyle(viewport).transform
    const matrix = transform.match(/matrix\(([^)]+)\)/)?.[1]?.split(',').map((value) => Number(value.trim())) || []
    return {
      flowLeft: flowRect.left,
      flowWidth: flowRect.width,
      flowRight: flowRect.right,
      nodeLeft: nodeRect.left,
      nodeTop: nodeRect.top,
      nodeRight: nodeRect.right,
      nodeBottom: nodeRect.bottom,
      nodeWidth: nodeRect.width,
      nodeHeight: nodeRect.height,
      viewportTransform: transform,
      viewportScale: Number.isFinite(matrix[0]) ? matrix[0] : 1,
      viewportTranslateX: Number.isFinite(matrix[4]) ? matrix[4] : 0,
      viewportTranslateY: Number.isFinite(matrix[5]) ? matrix[5] : 0,
      zoomLabel: zoomLabel?.textContent?.trim() || '',
    }
  }, nodeSelector)
}

async function panelMetrics(page) {
  return page.evaluate(() => {
    const rect = (selector) => {
      const element = document.querySelector(selector)
      if (!element) return null
      const box = element.getBoundingClientRect()
      const style = window.getComputedStyle(element)
      return {
        left: box.left,
        right: box.right,
        top: box.top,
        bottom: box.bottom,
        width: box.width,
        height: box.height,
        zIndex: Number.parseInt(style.zIndex || '0', 10) || 0,
      }
    }
    return {
      viewportWidth: window.innerWidth,
      drawer: rect('[data-testid="node-test-drawer"]'),
      config: rect('[data-testid="node-config-panel"]'),
      toolbar: rect('[data-testid="canvas-bottom-toolbar"]'),
      debugDock: rect('[data-testid="workflow-debug-dock"]'),
    }
  })
}

function assertStableMetrics(before, after, label) {
  assert(
    Math.abs(before.flowWidth - after.flowWidth) <= 1,
    `${label}: flow width changed from ${before.flowWidth} to ${after.flowWidth}`,
  )
  assert(
    Math.abs(before.nodeWidth - after.nodeWidth) <= 1,
    `${label}: node width changed from ${before.nodeWidth} to ${after.nodeWidth}`,
  )
  assert(
    Math.abs(before.nodeHeight - after.nodeHeight) <= 1,
    `${label}: node height changed from ${before.nodeHeight} to ${after.nodeHeight}`,
  )
  assert(
    Math.abs(before.nodeLeft - after.nodeLeft) <= 1,
    `${label}: node left changed from ${before.nodeLeft} to ${after.nodeLeft}`,
  )
  assert(
    Math.abs(before.nodeTop - after.nodeTop) <= 1,
    `${label}: node top changed from ${before.nodeTop} to ${after.nodeTop}`,
  )
  assert(
    Math.abs(before.viewportScale - after.viewportScale) <= 0.01,
    `${label}: viewport scale changed from ${before.viewportScale} to ${after.viewportScale}`,
  )
  assert(
    Math.abs(before.viewportTranslateX - after.viewportTranslateX) <= 1,
    `${label}: viewport translateX changed from ${before.viewportTranslateX} to ${after.viewportTranslateX}`,
  )
  assert(
    Math.abs(before.viewportTranslateY - after.viewportTranslateY) <= 1,
    `${label}: viewport translateY changed from ${before.viewportTranslateY} to ${after.viewportTranslateY}`,
  )
  assert(
    before.zoomLabel === after.zoomLabel,
    `${label}: zoom label changed from ${before.zoomLabel} to ${after.zoomLabel}`,
  )
}

async function createFlow(page, endpoint, namePrefix) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/${endpoint}`, {
      data: {
        name: `${namePrefix} ${Date.now()}`,
        description: 'opening config panel must not resize or refit the canvas',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['input'], ui: { position: { x: 160, y: 180 } } } },
          { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { inputParameters: [{ name: 'input', value: '{{start.input}}' }], outputVariable: 'answer', ui: { position: { x: 520, y: 180 } } } },
          {
            nodeKey: 'variable_aggregation_1',
            type: 'VARIABLE_AGGREGATION',
            name: '变量聚合',
            config: {
              strategy: 'first_non_empty',
              groups: [
                {
                  name: 'selected',
                  type: 'string',
                  variables: [
                    { value: '{{start.input}}', type: 'string' },
                    { value: '{{llm_1.answer}}', type: 'string' },
                  ],
                },
              ],
              outputParameters: [{ name: 'selected', type: 'string' }],
              ui: { position: { x: 520, y: 420 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { output: '{{llm_1.answer}}', ui: { position: { x: 920, y: 180 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    `create ${endpoint}`,
  )
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  try {
    async function assertNodeStable(nodeSelector, label) {
    await page.locator(nodeSelector).waitFor({ state: 'visible', timeout: 10000 })
    const beforeOpen = await canvasMetrics(page, nodeSelector)

    await page.locator(nodeSelector).click()
    const panel = page.locator('[data-testid="node-config-panel"]')
    await panel.waitFor({ state: 'visible', timeout: 5000 })
    await page.waitForTimeout(260)
    const afterOpen = await canvasMetrics(page, nodeSelector)
    assertStableMetrics(beforeOpen, afterOpen, `opening ${label} config panel`)

    await panel.getByRole('button', { name: '关闭配置' }).click()
    await panel.waitFor({ state: 'hidden', timeout: 5000 })
    await page.waitForTimeout(260)
    const afterClose = await canvasMetrics(page, nodeSelector)
    assertStableMetrics(beforeOpen, afterClose, `closing ${label} config panel`)
  }

  async function assertNodeTestDrawerStable(nodeSelector, label) {
    await page.locator(nodeSelector).waitFor({ state: 'visible', timeout: 10000 })
    await page.locator(nodeSelector).click()
    const panel = page.locator('[data-testid="node-config-panel"]')
    await panel.waitFor({ state: 'visible', timeout: 5000 })
    await page.waitForTimeout(260)
    const beforeDrawer = await canvasMetrics(page, nodeSelector)

    await panel.getByRole('button', { name: '试运行当前节点', exact: true }).click()
    const drawer = page.locator('[data-testid="node-test-drawer"]')
    await drawer.waitFor({ state: 'visible', timeout: 5000 })
    await page.waitForTimeout(320)
    const afterDrawerOpen = await canvasMetrics(page, nodeSelector)
    assertStableMetrics(beforeDrawer, afterDrawerOpen, `opening ${label} selected-node test drawer`)

    const openMetrics = await panelMetrics(page)
    assert(openMetrics.drawer, `Expected ${label} node test drawer metrics`)
    assert(openMetrics.toolbar, `Expected ${label} canvas toolbar metrics`)
    assert(
      openMetrics.drawer.zIndex > openMetrics.toolbar.zIndex,
      `${label}: node test drawer must layer above toolbar, got ${JSON.stringify(openMetrics)}`,
    )
    if (openMetrics.debugDock) {
      assert(
        openMetrics.drawer.zIndex > openMetrics.debugDock.zIndex,
        `${label}: node test drawer must layer above debug dock, got ${JSON.stringify(openMetrics)}`,
      )
    }
    if (openMetrics.config) {
      assert(
        openMetrics.drawer.zIndex > openMetrics.config.zIndex,
        `${label}: node test drawer must be the top floating panel, got ${JSON.stringify(openMetrics)}`,
      )
    }

    await panel.getByRole('button', { name: '关闭配置', exact: true }).click()
    await panel.waitFor({ state: 'hidden', timeout: 5000 })
    await page.waitForTimeout(320)
    const afterConfigClose = await canvasMetrics(page, nodeSelector)
    assertStableMetrics(beforeDrawer, afterConfigClose, `closing ${label} config while node test drawer remains open`)
    const closedMetrics = await panelMetrics(page)
    assert(closedMetrics.drawer, `Expected ${label} node test drawer to remain visible after closing config`)
    assert(
      Math.abs(closedMetrics.viewportWidth - closedMetrics.drawer.right - 10) <= 2,
      `${label}: node test drawer should snap to the screen right gutter when the right panel closes, got ${JSON.stringify(closedMetrics)}`,
    )

    await drawer.getByRole('button', { name: '关闭节点试运行', exact: true }).click()
    await drawer.waitFor({ state: 'hidden', timeout: 5000 })
    await page.waitForTimeout(260)
    const afterDrawerClose = await canvasMetrics(page, nodeSelector)
    assertStableMetrics(beforeDrawer, afterDrawerClose, `closing ${label} selected-node test drawer`)
  }

  const workflow = await createFlow(page, 'workflows', 'Workflow Config Zoom Stability')
  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await assertNodeStable('.coze-node.node-llm', 'LLM')
  await assertNodeStable('.coze-node.node-variable_aggregation', 'variable aggregation')
  await assertNodeTestDrawerStable('.coze-node.node-llm', 'workflow LLM')

  const chatflow = await createFlow(page, 'chatflows', 'Chatflow Config Zoom Stability')
  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await assertNodeStable('.coze-node.node-llm', 'chatflow LLM')
  await assertNodeStable('.coze-node.node-variable_aggregation', 'chatflow variable aggregation')
  await assertNodeTestDrawerStable('.coze-node.node-llm', 'chatflow LLM')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow/chatflow config panel zoom stability e2e')
} finally {
  await browser.close()
}
