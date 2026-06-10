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
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `Node Card Actions ${Date.now()}`,
        description: 'node card action menu e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 180 } } } },
          { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { outputVariable: 'answer', ui: { position: { x: 500, y: 160 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{llm_1.answer}}', ui: { position: { x: 880, y: 180 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create workflow for node card actions',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  const startNode = page.locator('.vue-flow__node[data-id="start"]')
  const endNode = page.locator('.vue-flow__node[data-id="end"]')
  await startNode.waitFor({ state: 'visible', timeout: 5000 })
  await endNode.waitFor({ state: 'visible', timeout: 5000 })
  await startNode.hover()
  assert(await startNode.getByRole('button', { name: '更多操作', exact: true }).count() === 0, 'START card should not expose action buttons')
  await endNode.hover()
  assert(await endNode.getByRole('button', { name: '更多操作', exact: true }).count() === 0, 'END card should not expose action buttons')

  const llmNode = page.locator('.vue-flow__node[data-id="llm_1"]')
  await llmNode.waitFor({ state: 'visible', timeout: 5000 })
  await llmNode.hover()

  assert(await llmNode.getByRole('button', { name: '试运行当前节点', exact: true }).count() === 1, 'Expected node card run button')
  assert(await llmNode.getByRole('button', { name: '更多操作', exact: true }).count() === 1, 'Expected node card more button')
  const actionStyle = await llmNode.getByRole('button', { name: '更多操作', exact: true }).evaluate((button) => {
    const style = getComputedStyle(button)
    return { backgroundColor: style.backgroundColor, borderStyle: style.borderStyle, borderWidth: style.borderWidth }
  })
  assert(actionStyle.backgroundColor === 'rgba(0, 0, 0, 0)' && actionStyle.borderStyle === 'none', `Expected icon-only transparent action style ${JSON.stringify(actionStyle)}`)

  await llmNode.getByRole('button', { name: '更多操作', exact: true }).click()
  const menu = page.getByTestId('node-card-menu')
  await menu.waitFor({ state: 'visible', timeout: 5000 })
  for (const label of ['重命名', '创建副本', '删除', '帮助文档']) {
    assert(await menu.getByRole('menuitem', { name: label, exact: true }).count() === 1, `Expected menu item ${label}`)
  }

  await menu.getByRole('menuitem', { name: '重命名', exact: true }).click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  if (await panel.getByRole('button', { name: '编辑节点名称', exact: true }).count()) {
    await panel.getByRole('button', { name: '编辑节点名称', exact: true }).click()
  }
  const nameInput = panel.getByRole('textbox', { name: '节点名称', exact: true })
  await nameInput.fill('大模型改名')
  await nameInput.press('Enter')
  await page.locator('.vue-flow__node[data-id="llm_1"] .node-title', { hasText: '大模型改名' }).waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByRole('button', { name: '编辑节点名称', exact: true }).click()
  await nameInput.fill('大模型二次改名')
  await panel.getByRole('button', { name: '确认节点名称', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"] .node-title', { hasText: '大模型二次改名' }).waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByRole('button', { name: '关闭配置', exact: true }).click()

  await llmNode.hover()
  await llmNode.getByRole('button', { name: '更多操作', exact: true }).click()
  await menu.getByRole('menuitem', { name: '创建副本', exact: true }).click()
  await page.locator('.coze-node', { hasText: '大模型二次改名 副本' }).waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByRole('button', { name: '关闭配置', exact: true }).click()

  const duplicate = page.locator('.coze-node', { hasText: '大模型二次改名 副本' }).first()
  await duplicate.hover()
  await duplicate.getByRole('button', { name: '更多操作', exact: true }).click()
  await menu.getByRole('menuitem', { name: '删除', exact: true }).click()
  await page.locator('.coze-node', { hasText: '大模型二次改名 副本' }).waitFor({ state: 'hidden', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow node card actions e2e')
} finally {
  await browser.close()
}
