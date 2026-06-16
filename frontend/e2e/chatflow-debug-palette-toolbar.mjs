import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'

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
        name: `Debug Palette Toolbar ${Date.now()}`,
        description: 'debug palette toolbar e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 160, y: 240 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.sys.query}}', ui: { position: { x: 760, y: 240 } } } },
        ],
        edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
      },
    }),
    'create chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  const toolbar = page.getByTestId('canvas-bottom-toolbar')
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })
  await toolbar.getByRole('button', { name: '调试工具', exact: true }).click()
  await page.getByTestId('workflow-debug-dock').waitFor({ state: 'visible', timeout: 5000 })
  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').waitFor({ state: 'visible', timeout: 5000 })
  await page.getByRole('button', { name: '关闭调试工具', exact: true }).click()
  await page.getByTestId('workflow-debug-dock').waitFor({ state: 'hidden', timeout: 5000 })

  const state = await page.evaluate(() => {
    const toolbarElement = document.querySelector('[data-testid="canvas-bottom-toolbar"]')
    return {
      paletteCount: document.querySelectorAll('[data-testid="bottom-node-palette"]').length,
      toolbarBottom: toolbarElement ? Number.parseFloat(getComputedStyle(toolbarElement).bottom) : -1,
    }
  })
  assert(state.paletteCount === 0, `Expected node palette to close with debug dock, got ${JSON.stringify(state)}`)
  assert(state.toolbarBottom >= 0 && state.toolbarBottom < 48, `Expected toolbar to return near bottom, got ${JSON.stringify(state)}`)

  console.log('PASS chatflow debug palette toolbar e2e')
} finally {
  await browser.close()
}
