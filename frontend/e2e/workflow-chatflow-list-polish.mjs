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

async function seedWorkflow(page, stamp) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `列表工作流 ${stamp}`,
      description: 'workflow list polish seed',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 120 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.USER_INPUT}}', ui: { position: { x: 520, y: 120 } } } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'seed workflow list item')
}

async function seedChatflow(page, stamp) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `列表对话流 ${stamp}`,
      description: 'chatflow list polish seed',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 120 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.USER_INPUT}}', ui: { position: { x: 520, y: 120 } } } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'seed chatflow list item')
}

async function assertList(page, path, title, createLabel) {
  await page.goto(`${baseUrl}${path}`, { waitUntil: 'networkidle' })
  await page.getByRole('heading', { name: title, exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.getByRole('button', { name: createLabel, exact: true }).count() === 1, `Expected create button ${createLabel}`)
  const tabText = await page.locator('.workflow-module-tabs').innerText()
  assert(tabText.includes('工作流') && tabText.includes('对话流'), `Expected Chinese module tabs, got ${tabText}`)
  assert(!tabText.includes('Workflow') && !tabText.includes('Chatflow'), `Module tabs must be Chinese, got ${tabText}`)

  const table = page.locator('.workflow-table')
  await table.waitFor({ state: 'visible', timeout: 5000 })
  const headerText = await table.locator('thead').innerText()
  for (const label of ['名称', '描述', '状态', '更新时间', '操作']) {
    assert(headerText.includes(label), `Expected table header ${label}, got ${headerText}`)
  }

  const actionButtons = ['查看', '画布']
  for (const label of actionButtons) {
    assert(await table.getByRole('button', { name: label, exact: true }).count() >= 1 || await page.locator('.empty-state').count() >= 1, `Expected action ${label}`)
  }

  const rowMetrics = await table.locator('tbody tr').first().evaluate((row) => {
    const rowRect = row.getBoundingClientRect()
    const actionButtons = Array.from(row.querySelectorAll('button')).map((button) => {
      const rect = button.getBoundingClientRect()
      return {
        text: button.textContent?.trim(),
        width: rect.width,
        height: rect.height,
        visible: rect.width > 0 && rect.height > 0,
      }
    })
    return { height: rowRect.height, actionButtons }
  })
  assert(rowMetrics.height < 96, `Expected compact list row height, got ${rowMetrics.height}`)
  for (const label of actionButtons) {
    const action = rowMetrics.actionButtons.find((button) => button.text === label)
    assert(action?.visible, `Expected visible action button ${label}, got ${JSON.stringify(rowMetrics.actionButtons)}`)
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()
  await seedWorkflow(page, stamp)
  await seedChatflow(page, stamp)
  await assertList(page, '/workflows', '工作流', '新建工作流')
  await assertList(page, '/chatflows', '对话流', '新建对话流')
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log('PASS workflow/chatflow list polish')
} finally {
  await browser.close()
}
