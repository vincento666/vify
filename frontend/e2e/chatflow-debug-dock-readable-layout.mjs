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
const page = await browser.newPage({ viewport: { width: 720, height: 900 } })

try {
  const stamp = Date.now()
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `021 readable debug panel ${stamp}`,
      description: 'chatflow debug panel must remain readable on constrained canvas widths',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 120, y: 180 } } } },
        { nodeKey: 'message_1', type: 'MESSAGE', name: '消息', config: { content: `Readable debug ${stamp}: {{start.sys.query}}`, outputVariable: 'content', ui: { position: { x: 520, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{message_1.content}}', ui: { position: { x: 900, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
        { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create chatflow')

  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
    data: {
      input: {
        'sys.query': `readability-${stamp}`,
        'sys.conversation_id': `conv-readable-${stamp}`,
        'sys.user_id': `user-readable-${stamp}`,
        'sys.channel': 'web',
      },
    },
  }), 'run chatflow')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas?runId=${run.runId}&debug=1`, { waitUntil: 'networkidle' })
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.waitFor({ state: 'visible', timeout: 10000 })
  await dock.getByText(`Run #${run.runId}`, { exact: false }).waitFor({ state: 'visible', timeout: 10000 })

  const box = await dock.boundingBox()
  assert(box, 'Expected debug dock bounding box')
  assert(box.width >= 560, `Expected readable debug panel width >= 560px, got ${box.width}`)
  assert(box.height >= 260, `Expected bottom debug dock height >= 260px, got ${box.height}`)
  assert(box.x + box.width <= 720, `Expected debug panel to stay inside viewport, got x=${box.x} width=${box.width}`)
  assert(box.y > 300, `Expected Coze-style bottom debug dock, got y=${box.y}`)

  const toolbar = page.getByTestId('canvas-bottom-toolbar')
  assert(await toolbar.getByRole('button', { name: '画布面板', exact: true }).count() === 0, 'Expected no duplicate hide-all canvas panel button')
  assert(await toolbar.getByRole('button', { name: '角色', exact: true }).count() === 0, 'Expected unused role toolbar button to stay removed')

  const toolbarBox = await toolbar.boundingBox()
  assert(toolbarBox, 'Expected canvas toolbar bounding box')
  assert(toolbarBox.y < box.y, `Expected toolbar above bottom debug dock, got toolbar y=${toolbarBox.y} dock y=${box.y}`)
  assert(box.y + box.height >= 880, `Expected debug dock near viewport bottom edge, got bottom=${box.y + box.height}`)

  const dockText = await dock.innerText()
  assert(dockText.includes(`Run #${run.runId}`), `Expected run id in readable dock, got ${dockText}`)
  assert(dockText.includes('调用树'), 'Expected call tree section in readable dock')
  assert(dockText.includes('详情'), 'Expected Coze-style detail section in readable dock')
  assert(dockText.includes('火焰图'), 'Expected flamegraph detail mode in readable dock')
  assert(dockText.includes('节点详情'), 'Expected node detail in readable dock')
  assert(dockText.includes('message_1'), 'Expected message node detail in readable dock')
  assert(!dockText.includes('事件时间线'), 'Expected event timeline to be hidden in advanced context by default')
  assert(!dockText.includes('作用域变量'), 'Expected scoped variables to be hidden in advanced context by default')

  assert(await dock.getByTestId('chatflow-run-call-tree').isVisible(), 'Expected call tree to stay visible beside detail area')
  const callTreeText = await dock.getByTestId('chatflow-run-call-tree').innerText()
  assert(!callTreeText.includes('start'), `Expected call tree to hide START node, got ${callTreeText}`)
  assert(!callTreeText.includes('end'), `Expected call tree to hide END node, got ${callTreeText}`)
  assert(await dock.locator('.workflow-call-tree-branch.depth-1').count() === 0, 'Expected ordinary canvas nodes to stay at the same call-tree level')
  const initialDetailMode = await dock.getByLabel('调试详情视图').inputValue()
  assert(initialDetailMode === 'flame', `Expected flamegraph to be the default detail mode, got ${initialDetailMode}`)
  const detailSelect = dock.getByLabel('调试详情视图')
  await detailSelect.selectOption('flame')
  const flameText = await dock.innerText()
  assert(flameText.includes('火焰图'), 'Expected flamegraph to render in detail area')
  assert(flameText.includes('message_1'), 'Expected flamegraph node to be selectable')

  await dock.getByTestId('chatflow-run-call-tree').getByRole('button', { name: 'message_1', exact: false }).click()
  await detailSelect.selectOption('node')
  const selectedText = await dock.innerText()
  assert(selectedText.includes('节点详情'), 'Expected selected node detail after call-tree click')
  assert(selectedText.includes('Readable debug'), 'Expected selected node output in detail')

  const succeededNodeBadges = await page.locator('.coze-node .node-run-status.status-succeeded').count()
  assert(succeededNodeBadges >= 3, `Expected canvas node cards to show run status badges, got ${succeededNodeBadges}`)
  const statusIcons = await page.locator('.coze-node .node-run-status-icon').count()
  assert(statusIcons >= 3, `Expected canvas node run status badges to include icons, got ${statusIcons}`)

  const messageNode = page.locator('.coze-node').filter({ hasText: '消息' }).first()
  const titleRun = messageNode.locator('.node-title-run')
  assert(await titleRun.count() === 1, 'Expected node title and run status to share one inline group')
  const titleBox = await titleRun.locator('.node-title').boundingBox()
  const badgeBox = await titleRun.locator('.node-run-status').boundingBox()
  assert(titleBox && badgeBox, 'Expected node title and status bounding boxes')
  assert(badgeBox.x > titleBox.x + titleBox.width - 1, 'Expected run status to sit to the right of node title')
  assert(badgeBox.x - (titleBox.x + titleBox.width) <= 14, `Expected run status to be adjacent to title, gap=${badgeBox.x - (titleBox.x + titleBox.width)}`)

  const nodeIconStyle = await messageNode.locator('.node-type-icon').evaluate((element) => {
    const style = window.getComputedStyle(element)
    const svg = element.querySelector('svg')
    return {
      backgroundColor: style.backgroundColor,
      color: style.color,
      svgWidth: svg ? window.getComputedStyle(svg).width : '',
      svgStrokeWidth: svg ? svg.getAttribute('stroke-width') || window.getComputedStyle(svg).strokeWidth : '',
    }
  })
  assert(nodeIconStyle.color !== 'rgb(255, 255, 255)', `Expected lightweight colored glyph icon, got ${JSON.stringify(nodeIconStyle)}`)

  const bodyOverflow = await dock.locator('.debug-dock-body').evaluate((element) => window.getComputedStyle(element).overflowY)
  assert(bodyOverflow === 'auto' || bodyOverflow === 'scroll', `Expected debug dock body to scroll vertically, got overflowY=${bodyOverflow}`)

  await detailSelect.selectOption('flame')
  await dock.getByTestId('chatflow-run-flamegraph').waitFor({ state: 'visible', timeout: 5000 })
  const flameBarBox = await dock.locator('.workflow-flame-bar').first().boundingBox()
  assert(flameBarBox && flameBarBox.width >= 120 && flameBarBox.height >= 28, `Expected visible flamegraph bar, got ${JSON.stringify(flameBarBox)}`)
  assert(await dock.locator('.workflow-flame-axis').count() === 1, 'Expected Coze-style flamegraph time axis')

  if (screenshotPath) {
    await dock.locator('.workflow-flame-bar').first().scrollIntoViewIfNeeded()
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS chatflow debug dock readable layout chatflow=${chatflow.id} run=${run.runId}`)
} finally {
  await browser.close()
}
