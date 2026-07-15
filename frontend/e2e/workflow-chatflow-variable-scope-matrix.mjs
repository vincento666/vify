import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''

const flows = [
  { label: 'workflow', api: 'workflows', path: 'workflows', startVariables: ['USER_INPUT'] },
  { label: 'chatflow', api: 'chatflows', path: 'chatflows', startVariables: ['sys.query', 'sys.conversation_id'] },
]

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  if (!response.ok()) throw new Error(`${label} HTTP ${response.status()} ${await response.text()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

function fixturePayload(flow) {
  const stamp = Date.now()
  const startReference = flow.label === 'chatflow' ? '{{start.sys.query}}' : '{{start.USER_INPUT}}'
  return {
    name: `Spec 225 variable scope ${flow.label} ${stamp}`,
    description: 'temporary cleanable variable scope browser matrix fixture',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: flow.startVariables, ui: { position: { x: 120, y: 240 } } } },
      {
        nodeKey: 'upstream_1',
        type: 'TEXT_PROCESS',
        name: '上游文本',
        config: {
          operation: 'format_template',
          template: `upstream ${startReference}`,
          outputParameters: [{ name: 'upstream_text', type: 'string' }],
          ui: { position: { x: 420, y: 140 } },
        },
      },
      {
        nodeKey: 'sibling_1',
        type: 'TEXT_PROCESS',
        name: '旁路文本',
        config: {
          operation: 'format_template',
          template: `sibling ${startReference}`,
          outputParameters: [{ name: 'sibling_only', type: 'string' }],
          ui: { position: { x: 420, y: 360 } },
        },
      },
      {
        nodeKey: 'message_1',
        type: 'MESSAGE',
        name: '消息',
        config: {
          inputParameters: [{ name: 'message_input', type: 'string', valueMode: 'reference', value: '{{upstream_1.upstream_text}}' }],
          content: '{{message_input}}',
          outputParameters: [{ name: 'content', type: 'string' }],
          ui: { position: { x: 760, y: 140 } },
        },
      },
      { nodeKey: 'end', type: 'END', name: '结束', config: { output: '{{message_1.content}}', ui: { position: { x: 1080, y: 140 } } } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'upstream_1', condition: null },
      { sourceNodeKey: 'start', targetNodeKey: 'sibling_1', condition: null },
      { sourceNodeKey: 'upstream_1', targetNodeKey: 'message_1', condition: null },
      { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
    ],
  }
}

async function closeConfigPanel(page) {
  const panel = page.getByTestId('node-config-panel')
  if (!(await panel.isVisible().catch(() => false))) return
  await panel.getByRole('button', { name: '关闭配置', exact: true }).click()
  await panel.waitFor({ state: 'hidden', timeout: 10000 })
}

async function openMessagePanel(page) {
  await closeConfigPanel(page)
  const node = page.locator('.vue-flow__node[data-id="message_1"]')
  await node.waitFor({ state: 'visible', timeout: 10000 })
  await node.click({ force: true })
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  const inputSection = panel.getByTestId('config-section-输入')
  await inputSection.waitFor({ state: 'visible', timeout: 10000 })
  const toggle = inputSection.locator('.config-section-toggle[aria-expanded="false"]')
  if (await toggle.count()) await toggle.click()
  return panel
}

async function auditScope(page, flow) {
  await page.goto(`${baseUrl}/${flow.path}/${flow.id}/canvas`, { waitUntil: 'networkidle' })
  const panel = await openMessagePanel(page)

  await panel.getByRole('button', { name: '选择输入变量', exact: true }).click()
  const inputPicker = panel.getByTestId('input-variable-picker')
  await inputPicker.waitFor({ state: 'visible', timeout: 10000 })
  const sourceText = await inputPicker.getByTestId('input-variable-source-list').innerText()
  assert(sourceText.includes('开始'), `${flow.label} input picker must include START, got ${sourceText}`)
  assert(sourceText.includes('上游文本'), `${flow.label} input picker must include connected upstream output, got ${sourceText}`)
  assert(!sourceText.includes('旁路文本'), `${flow.label} input picker must hide sibling branch, got ${sourceText}`)

  await inputPicker.getByTestId('input-variable-source-item').filter({ hasText: '上游文本' }).click()
  const upstreamItems = await inputPicker.getByTestId('input-variable-item-list').innerText()
  assert(upstreamItems.includes('upstream_text'), `${flow.label} upstream picker must expose upstream_text, got ${upstreamItems}`)
  assert(!upstreamItems.includes('sibling_only'), `${flow.label} upstream picker must not expose sibling_only, got ${upstreamItems}`)
  await panel.getByRole('button', { name: '选择输入变量', exact: true }).click()
  await inputPicker.waitFor({ state: 'hidden', timeout: 10000 })

  const content = panel.getByPlaceholder('可使用变量引用', { exact: true })
  await content.fill('')
  await page.waitForTimeout(50)
  await content.fill('{{')
  const inlinePicker = panel.getByTestId('variable-picker')
  await inlinePicker.waitFor({ state: 'visible', timeout: 10000 })
  const inlineText = await inlinePicker.getByTestId('inline-variable-list').innerText()
  assert(inlineText.includes('message_input'), `${flow.label} message content must expose its local input, got ${inlineText}`)
  assert(!inlineText.includes('upstream_text'), `${flow.label} message content must not expose upstream global reference, got ${inlineText}`)
  assert(!inlineText.includes('sibling_only'), `${flow.label} message content must not expose sibling reference, got ${inlineText}`)
  assert(!inlineText.includes('USER_INPUT'), `${flow.label} message content must not expose START globals, got ${inlineText}`)
  assert(!inlineText.includes('sys.query'), `${flow.label} message content must not expose START globals, got ${inlineText}`)

  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/${flow.label}-message-local-picker.png`, fullPage: true })
  await inlinePicker.getByTestId('variable-option', { hasText: 'message_input' }).click()
  assert((await content.inputValue()).includes('{{message_input}}'), `${flow.label} local inline picker must insert local reference`)

  const saveResponse = page.waitForResponse((candidate) =>
    candidate.url().includes(`/api/v1/${flow.api}/${flow.id}`) && candidate.request().method() === 'PUT',
  )
  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await unwrap(await saveResponse, `save ${flow.label}`)
  const saved = await unwrap(await page.request.get(`${baseUrl}/api/v1/${flow.api}/${flow.id}`), `reload ${flow.label}`)
  const message = saved.nodes.find((node) => node.nodeKey === 'message_1')
  assert(message?.config?.content === '{{message_input}}', `${flow.label} local content reference must persist, got ${JSON.stringify(message?.config)}`)
}

async function cleanupFlows(page, created) {
  const failures = []
  for (const flow of created.reverse()) {
    try {
      await unwrap(await page.request.delete(`${baseUrl}/api/v1/${flow.api}/${flow.id}`), `cleanup ${flow.label}`)
    } catch (error) {
      failures.push(error instanceof Error ? error.message : String(error))
    }
  }
  assert(failures.length === 0, `Fixture cleanup failed: ${failures.join(' | ')}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const created = []

try {
  for (const template of flows) {
    const createdFlow = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/${template.api}`, { data: fixturePayload(template) }),
      `create ${template.label}`,
    )
    const flow = { ...template, id: createdFlow.id }
    created.push(flow)
    await auditScope(page, flow)
  }
  console.log('PASS workflow/chatflow variable scope matrix e2e')
} finally {
  try {
    await cleanupFlows(page, created)
  } finally {
    await browser.close()
  }
}
