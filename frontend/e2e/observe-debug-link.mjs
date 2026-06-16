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
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `019.4 Debug Observe Link ${stamp}`,
      description: 'debug dock observe link e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'handoff_1',
          type: 'TRANSFER_TO_HUMAN',
          name: '转人工',
          config: {
            queue: 'debug-observe',
            message: '已切到人工队列。',
            ui: { position: { x: 500, y: 180 } },
          },
        },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'done', ui: { position: { x: 860, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'handoff_1', condition: null },
        { sourceNodeKey: 'handoff_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create chatflow')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '对话试运行', exact: true }).click()
  const panel = page.getByTestId('test-run-panel')
  await panel.getByTestId('chatflow-run-fields-toggle').click()
  await panel.getByPlaceholder('输入消息').fill('请转人工并记录观测链路')
  await panel.getByPlaceholder('conversation_id').fill(`debug-observe-${stamp}`)
  await panel.getByPlaceholder('user_id').fill(`debug-user-${stamp}`)
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()
  await panel.getByText('INTERRUPTED', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  const runSummary = await panel.locator('.chatflow-run-meta').textContent()
  const runId = Number(runSummary.match(/Run #(\d+)/)?.[1] || 0)
  assert(runId > 0, `Expected run id in summary, got ${runSummary}`)

  await page.getByRole('button', { name: '调试工具', exact: true }).click()
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByTestId('debug-observe-link').waitFor({ state: 'visible', timeout: 10000 })
  await dock.getByTestId('debug-observe-link').click()

  await page.waitForURL(`${baseUrl}/chatflows/${chatflow.id}/canvas?runId=${runId}&debug=1`, { timeout: 10000 })
  assert(!page.url().includes('/observe'), `Expected composer debug URL, got ${page.url()}`)
  await dock.getByText(`Run #${runId}`, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  const detailText = await dock.textContent()
  assert(detailText.includes('转人工'), 'Expected embedded detail to include handoff event after debug link')
  assert(detailText.includes('handoff_1'), 'Expected embedded detail to include handoff node after debug link')
  assert(await page.getByTestId('observe-run-detail').count() === 0, 'Standalone observe detail should not render')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS observe debug link e2e chatflow=${chatflow.id} run=${runId}`)
} finally {
  await browser.close()
}
