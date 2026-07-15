import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''

const flows = [
  { label: 'workflow', api: 'workflows', path: 'workflows' },
  { label: 'chatflow', api: 'chatflows', path: 'chatflows' },
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

function fixturePayload(label) {
  const stamp = Date.now()
  return {
    name: `Spec 225 chevron icon ${label} ${stamp}`,
    description: 'temporary cleanable fixture for Workflow/Chatflow chevron icon UAT',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 240 } } },
      },
      {
        nodeKey: 'assign_1',
        type: 'VARIABLE_ASSIGN',
        name: '变量赋值',
        config: {
          targetScope: 'flow',
          targetVariable: 'topic',
          sourceValueMode: 'literal',
          source: 'seed',
          ui: { position: { x: 480, y: 240 } },
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: { output: '{{assign_1.topic}}', ui: { position: { x: 840, y: 240 } } },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'assign_1', condition: null },
      { sourceNodeKey: 'assign_1', targetNodeKey: 'end', condition: null },
    ],
  }
}

async function closeConfigPanel(page) {
  const panel = page.getByTestId('node-config-panel')
  if (!(await panel.isVisible().catch(() => false))) return
  await panel.getByRole('button', { name: '关闭配置', exact: true }).click()
  await panel.waitFor({ state: 'hidden', timeout: 10000 })
}

async function openNodePanel(page, nodeKey, expectedTestId) {
  await closeConfigPanel(page)
  const node = page.locator(`.vue-flow__node[data-id="${nodeKey}"]`)
  await node.waitFor({ state: 'visible', timeout: 10000 })
  await node.click({ force: true })
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByTestId(expectedTestId).waitFor({ state: 'visible', timeout: 10000 })
  return panel
}

async function assertSvgOnly(locator, label) {
  const count = await locator.count()
  assert(count > 0, `${label} must exist`)
  for (let index = 0; index < count; index += 1) {
    const item = locator.nth(index)
    const text = (await item.textContent() || '').trim()
    assert(text === '', `${label} must not render a text glyph, got ${JSON.stringify(text)}`)
    const tagName = await item.evaluate((element) => element.tagName.toLowerCase())
    const svgCount = tagName === 'svg' ? 1 : await item.locator('svg').count()
    assert(svgCount === 1, `${label} must render one SVG icon`)
  }
}

async function auditIcons(page, flow) {
  await page.goto(`${baseUrl}/${flow.path}/${flow.id}/canvas`, { waitUntil: 'networkidle' })

  await page.getByRole('button', { name: '开放', exact: true }).click()
  const openSurface = page.getByTestId('workflow-open-surface')
  await openSurface.waitFor({ state: 'visible', timeout: 10000 })
  await assertSvgOnly(openSurface.locator('.section-title-chevron'), `${flow.label} Open section chevron`)

  await page.getByRole('button', { name: '编排', exact: true }).click()
  const panel = await openNodePanel(page, 'assign_1', 'variable-assignment-editor')
  await assertSvgOnly(panel.locator('.section-chevron'), `${flow.label} config section chevron`)

  await panel.getByRole('button', { name: '选择赋值内容变量', exact: true }).click()
  const picker = panel.getByTestId('structured-variable-picker')
  await picker.waitFor({ state: 'visible', timeout: 10000 })
  await assertSvgOnly(picker.getByTestId('variable-source-arrow'), `${flow.label} variable source arrow`)

  await page.getByRole('button', { name: '发布', exact: true }).click()
  const publishDialog = page.getByTestId('workflow-publish-dialog')
  await publishDialog.waitFor({ state: 'visible', timeout: 10000 })
  await assertSvgOnly(publishDialog.locator('.section-title-chevron'), `${flow.label} publish section chevron`)

  if (screenshotDir) {
    await page.screenshot({ path: `${screenshotDir}/${flow.label}-chevrons.png`, fullPage: true })
  }
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
    const flow = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/${template.api}`, { data: fixturePayload(template.label) }),
      `create ${template.label}`,
    )
    const entry = { ...template, id: flow.id }
    created.push(entry)
    await auditIcons(page, entry)
  }
  console.log('PASS workflow/chatflow chevron icon e2e')
} finally {
  try {
    await cleanupFlows(page, created)
  } finally {
    await browser.close()
  }
}
