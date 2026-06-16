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
  assert(activeV2.versionId === publishV2.id, `Expected active v2 versionId ${publishV2.id}, got ${activeV2.versionId}`)

  const targetedV1 = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/published-runs`, {
    data: { input: {}, versionId: publishV1.id },
  }), 'run targeted v1')
  assert(targetedV1.output.final === 'v1', `Expected targeted v1 output, got ${JSON.stringify(targetedV1)}`)
  assert(targetedV1.versionId === publishV1.id, `Expected targeted v1 versionId ${publishV1.id}, got ${targetedV1.versionId}`)
  assert(targetedV1.version === 1, `Expected targeted v1 version=1, got ${targetedV1.version}`)

  const targetedV2 = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/published-runs`, {
    data: { input: {}, versionId: publishV2.id },
  }), 'run targeted v2')
  assert(targetedV2.output.final === 'v2', `Expected targeted v2 output, got ${JSON.stringify(targetedV2)}`)
  assert(targetedV2.versionId === publishV2.id, `Expected targeted v2 versionId ${publishV2.id}, got ${targetedV2.versionId}`)

  const activeAfterTarget = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/published-runs`, {
    data: { input: {} },
  }), 'run active after targeted v1')
  assert(activeAfterTarget.output.final === 'v2', `Expected active v2 after targeted v1, got ${JSON.stringify(activeAfterTarget)}`)
  assert(activeAfterTarget.versionId === publishV2.id, 'Targeted historical run should not change active version')

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
  const versionTwoRow = versions.locator('.version-row').filter({ hasText: 'v2' }).first()
  await versionTwoRow.getByTestId('workflow-version-run').click()
  const targetedRunResult = versions.locator('.targeted-published-run-result')
  await targetedRunResult.waitFor({ state: 'visible', timeout: 10000 })
  const targetedRunText = await targetedRunResult.textContent()
  assert(targetedRunText?.includes('运行版本 v2'), `Expected targeted UI run v2, got ${targetedRunText}`)
  assert(targetedRunText?.includes(`versionId ${publishV2.id}`), `Expected targeted UI versionId ${publishV2.id}, got ${targetedRunText}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS workflow publish versions e2e workflow=${workflow.id} v1=${publishV1.id} v2=${publishV2.id}`)
} finally {
  await browser.close()
}
