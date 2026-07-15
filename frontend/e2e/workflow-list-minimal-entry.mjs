import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
let screenshotTaken = false

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function createFlow(page, path, name) {
  return unwrap(await page.request.post(`${baseUrl}${path}`, {
    data: {
      name,
      description: 'workflow/chatflow minimal list entry e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 160 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { ui: { position: { x: 560, y: 160 } } } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), `create ${path}`)
}

async function assertMinimalListEntry(page, listPath, canvasPath, resourcePath, name) {
  await page.goto(`${baseUrl}${listPath}`, { waitUntil: 'networkidle' })
  const row = page.locator('tr', { hasText: name })
  await row.waitFor({ state: 'visible', timeout: 10000 })

  const actionTexts = (await row.locator('td').last().getByRole('button').allTextContents()).map((text) => text.trim())
  assert(actionTexts.length === 1 && actionTexts[0] === '删除', `Expected only delete action for ${name}, got ${actionTexts.join(', ')}`)

  if (screenshotPath && !screenshotTaken) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
    screenshotTaken = true
  }

  await row.getByText(name, { exact: true }).click()
  await page.waitForURL(`**${canvasPath}`, { timeout: 10000 })
  assert(new URL(page.url()).pathname === canvasPath, `Expected canvas path ${canvasPath}, got ${page.url()}`)

  await page.goto(`${baseUrl}${listPath}`, { waitUntil: 'networkidle' })
  const deleteRow = page.locator('tr', { hasText: name })
  await deleteRow.waitFor({ state: 'visible', timeout: 10000 })
  const deletion = page.waitForResponse((candidate) =>
    candidate.url().endsWith(resourcePath) && candidate.request().method() === 'DELETE',
  )
  await deleteRow.getByRole('button', { name: '删除', exact: true }).click()
  const confirmation = page.getByRole('button', { name: '确认', exact: true })
  await confirmation.waitFor({ state: 'visible', timeout: 10000 })
  await confirmation.click()
  await unwrap(await deletion, `delete ${name}`)
  await deleteRow.waitFor({ state: 'hidden', timeout: 10000 })
  assert(new URL(page.url()).pathname === listPath, `Delete action navigated away from ${listPath}: ${page.url()}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })
const cleanup = []

try {
  const stamp = Date.now()
  const workflowName = `Workflow List Entry ${stamp}`
  const chatflowName = `Chatflow List Entry ${stamp}`
  const workflow = await createFlow(page, '/api/v1/workflows', workflowName)
  cleanup.push(`/api/v1/workflows/${workflow.id}`)
  const chatflow = await createFlow(page, '/api/v1/chatflows', chatflowName)
  cleanup.push(`/api/v1/chatflows/${chatflow.id}`)

  await assertMinimalListEntry(page, '/workflows', `/workflows/${workflow.id}/canvas`, `/api/v1/workflows/${workflow.id}`, workflowName)
  await assertMinimalListEntry(page, '/chatflows', `/chatflows/${chatflow.id}/canvas`, `/api/v1/chatflows/${chatflow.id}`, chatflowName)

  console.log(`PASS workflow/chatflow minimal list entry workflow=${workflow.id} chatflow=${chatflow.id}`)
} finally {
  for (const path of cleanup.reverse()) {
    await page.request.delete(`${baseUrl}${path}`).catch(() => {})
  }
  await browser.close()
}
