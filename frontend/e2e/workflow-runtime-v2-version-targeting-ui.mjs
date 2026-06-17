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
    data: { name: `125 Runtime v2 Version UI ${stamp}`, description: 'runtime v2 version targeting ui e2e', ...graph('v1') },
  }), 'create workflow')
  const publishV1 = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/publish`), 'publish v1')

  await unwrap(await page.request.put(`${baseUrl}/api/v1/workflows/${workflow.id}`, {
    data: { ...graph('v2') },
  }), 'update workflow v2')
  const publishV2 = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/publish`), 'publish v2')

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '发布', exact: true }).click()
  const versions = page.getByTestId('workflow-version-list')
  await versions.getByText('v2', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await versions.getByText('v1', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  const versionOneRow = versions.locator('.version-row').filter({ hasText: 'v1' }).first()
  await versionOneRow.getByTestId('workflow-version-run').waitFor({ state: 'visible', timeout: 10000 })
  await versionOneRow.getByTestId('workflow-version-run-v2').click()

  const runtimeV2Result = versions.getByTestId('workflow-version-run-v2-result')
  await runtimeV2Result.waitFor({ state: 'visible', timeout: 10000 })
  const resultText = await runtimeV2Result.textContent()
  assert(resultText?.includes('Runtime v2 版本 v1'), `Expected runtime v2 UI result for v1, got ${resultText}`)
  assert(resultText?.includes(`versionId ${publishV1.id}`), `Expected runtime v2 UI versionId ${publishV1.id}, got ${resultText}`)
  assert(/RUNNING|SUCCEEDED|COMPLETED|FAILED|INTERRUPTED|WAITING|CANCELLED/.test(resultText || ''), `Expected runtime v2 status, got ${resultText}`)
  assert(resultText?.includes('debugRef /api/v1/runtime-runs/'), `Expected runtime v2 debug/result ref, got ${resultText}`)
  assert(publishV2.version === 2, `Expected second published version to be v2, got ${publishV2.version}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS workflow runtime v2 version targeting UI e2e workflow=${workflow.id} v1=${publishV1.id} v2=${publishV2.id}`)
} finally {
  await browser.close()
}
