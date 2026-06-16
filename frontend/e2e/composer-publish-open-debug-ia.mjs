import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const workflowScreenshotPath = process.env.HIFY_E2E_WORKFLOW_SCREENSHOT
const chatflowScreenshotPath = process.env.HIFY_E2E_CHATFLOW_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function createWorkflow(page, stamp) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `021.12 Workflow IA ${stamp}`,
      description: 'publish/open/debug IA e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.USER_INPUT}}', ui: { position: { x: 680, y: 180 } } } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create workflow')
}

async function createChatflow(page, stamp) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `021.12 Chatflow IA ${stamp}`,
      description: 'publish/open/debug IA e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'hello {{sys.query}}', ui: { position: { x: 680, y: 180 } } } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create chatflow')
}

async function assertComposerIa(page, path, screenshotPath) {
  await page.goto(`${baseUrl}${path}`, { waitUntil: 'networkidle' })

  await page.getByRole('button', { name: '编排', exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  assert(await page.getByRole('button', { name: '统计', exact: true }).count() === 0, 'Expected unfinished 统计 tab to be hidden')
  assert(await page.getByRole('button', { name: '观测', exact: true }).count() === 0, 'Expected header 观测 action to be replaced')
  assert(await page.getByTestId('workflow-ops-panel').count() === 0, 'Expected mixed 发布与运维 panel to be removed')

  await page.getByRole('button', { name: '开放', exact: true }).click()
  const openSurface = page.getByTestId('workflow-open-surface')
  await openSurface.waitFor({ state: 'visible', timeout: 5000 })
  const openText = await openSurface.innerText()
  assert(openText.includes('/api/v1/'), 'Expected Open surface to show API endpoint')
  assert(!openText.includes('发布与运维'), 'Expected Open surface not to reuse mixed ops wording')
  assert(!openText.includes('运行观测'), 'Expected Open surface not to contain observe panel wording')
  assert(await page.getByTestId('workflow-ops-panel').count() === 0, 'Expected Open tab not to open right-side ops panel')

  await page.getByRole('button', { name: '发布', exact: true }).click()
  const publishDialog = page.getByTestId('workflow-publish-dialog')
  await publishDialog.waitFor({ state: 'visible', timeout: 5000 })
  const publishText = await publishDialog.innerText()
  assert(publishText.includes('发布检查'), 'Expected publish dialog to contain publish checks')
  assert(publishText.includes('版本'), 'Expected publish dialog to contain version metadata/history')
  assert(!publishText.includes('运行观测'), 'Expected publish dialog not to duplicate observe controls')
  assert(await page.getByTestId('workflow-ops-panel').count() === 0, 'Expected Publish not to open right-side ops panel')
  await page.keyboard.press('Escape')

  await page.getByRole('button', { name: /调试详情|运行详情/ }).click()
  const debugDock = page.getByTestId('workflow-debug-dock')
  await debugDock.waitFor({ state: 'visible', timeout: 5000 })
  assert(await debugDock.getByText('调试详情', { exact: true }).count() >= 1, 'Expected debug action to open the bottom debug dock')
  assert(await page.getByRole('button', { name: '统计', exact: true }).count() === 0, 'Expected debug action not to activate statistics')
  assert(await page.getByTestId('workflow-ops-panel').count() === 0, 'Expected debug action not to open right-side ops panel')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()
  const workflow = await createWorkflow(page, stamp)
  await assertComposerIa(page, `/workflows/${workflow.id}/canvas`, workflowScreenshotPath)

  const chatflow = await createChatflow(page, stamp)
  await assertComposerIa(page, `/chatflows/${chatflow.id}/canvas`, chatflowScreenshotPath)

  console.log(`PASS composer publish/open/debug IA e2e workflow=${workflow.id} chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
