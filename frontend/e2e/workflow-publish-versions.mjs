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

function graph(output) {
  return {
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
      { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output, ui: { position: { x: 640, y: 180 } } } },
    ],
    edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: { name: `019.3 Publish E2E ${stamp}`, description: 'publish e2e', ...graph('v1') },
  }), 'create workflow')
  const publishV1 = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/publish`), 'publish v1')

  await unwrap(await page.request.put(`${baseUrl}/api/v1/workflows/${workflow.id}`, {
    data: { ...graph('v2') },
  }), 'update workflow v2')
  const publishV2 = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/publish`), 'publish v2')
  const activeV2 = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/published-runs`, {
    data: { input: {} },
  }), 'run active v2')
  assert(activeV2.output.final === 'v2', `Expected active v2 output, got ${JSON.stringify(activeV2)}`)

  await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/versions/${publishV1.id}/rollback`), 'rollback v1')
  const activeV1 = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/published-runs`, {
    data: { input: {} },
  }), 'run active v1')
  assert(activeV1.output.final === 'v1', `Expected active v1 output, got ${JSON.stringify(activeV1)}`)
  assert(publishV2.version === 2, 'Expected second publish version=2')

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '发布', exact: true }).click()
  const versions = page.getByTestId('workflow-version-list')
  await versions.getByText('v2', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await versions.getByText('v1', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await versions.getByText('当前版本', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await versions.getByText('可回滚', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS workflow publish versions e2e workflow=${workflow.id} v1=${publishV1.id} v2=${publishV2.id}`)
} finally {
  await browser.close()
}
