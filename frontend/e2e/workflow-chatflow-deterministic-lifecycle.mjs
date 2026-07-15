import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''
const keepFixtures = process.env.HIFY_E2E_KEEP_FIXTURES === '1'

const flowTemplates = [
  {
    label: 'workflow',
    api: 'workflows',
    path: 'workflows',
    startVariables: ['USER_INPUT'],
    startReference: '{{start.USER_INPUT}}',
    directInput: (value) => ({ userMessage: value, USER_INPUT: value }),
  },
  {
    label: 'chatflow',
    api: 'chatflows',
    path: 'chatflows',
    startVariables: ['sys.query', 'sys.conversation_id', 'sys.user_id', 'sys.channel'],
    startReference: '{{start.sys.query}}',
    directInput: (value) => ({ 'sys.query': value }),
  },
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

function fixturePayload(template, stamp) {
  const marker = `SPEC225_${template.label.toUpperCase()}_${stamp}`
  const branch = (key, name, right, y) => ({
    key,
    name,
    logic: 'AND',
    conditions: [{ left: template.startReference, operator: 'contains', right }],
    ui: { position: { x: 420, y } },
  })
  const message = (nodeKey, name, text, y) => ({
    nodeKey,
    type: 'MESSAGE',
    name,
    config: {
      content: text,
      outputVariable: 'content',
      outputParameters: [{ name: 'content', type: 'string' }],
      streamOutput: 'enabled',
      streamTarget: 'message',
      fallbackMode: 'aggregate',
      ui: { position: { x: 820, y } },
    },
  })
  const routes = [
    { key: 'refund', input: 'refund', expected: `${marker}_REFUND` },
    { key: 'invoice', input: 'invoice', expected: `${marker}_INVOICE` },
    { key: 'default', input: 'other', expected: `${marker}_DEFAULT` },
  ]
  return {
    marker,
    routes,
    payload: {
      name: `Spec 225 lifecycle ${template.label} ${stamp}`,
      description: 'temporary cleanable deterministic browser lifecycle fixture',
      nodes: [
        {
          nodeKey: 'start',
          type: 'START',
          name: '开始',
          config: { outputVariables: template.startVariables, ui: { position: { x: 120, y: 240 } } },
        },
        {
          nodeKey: 'router',
          type: 'CONDITION',
          name: '多条件路由',
          config: {
            outputVariable: 'route',
            conditionBranches: [
              branch('refund', '退款分支', 'refund', 100),
              branch('invoice', '发票分支', 'invoice', 240),
            ],
            defaultBranch: 'default',
            defaultBranchName: '默认分支',
            ui: { position: { x: 420, y: 240 } },
          },
        },
        message('refund_message', '退款消息', `${marker}_REFUND ${template.startReference}`, 100),
        message('invoice_message', '发票消息', `${marker}_INVOICE ${template.startReference}`, 240),
        message('default_message', '默认消息', `${marker}_DEFAULT ${template.startReference}`, 380),
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: {
            outputVariable: 'final',
            output: '{{refund_message.content}}{{invoice_message.content}}{{default_message.content}}',
            ui: { position: { x: 1220, y: 240 } },
          },
        },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'router', condition: null },
        { sourceNodeKey: 'router', targetNodeKey: 'refund_message', condition: 'refund' },
        { sourceNodeKey: 'router', targetNodeKey: 'invoice_message', condition: 'invoice' },
        { sourceNodeKey: 'router', targetNodeKey: 'default_message', condition: null },
        { sourceNodeKey: 'refund_message', targetNodeKey: 'end', condition: null },
        { sourceNodeKey: 'invoice_message', targetNodeKey: 'end', condition: null },
        { sourceNodeKey: 'default_message', targetNodeKey: 'end', condition: null },
      ],
    },
  }
}

async function verifyDirectBranchMatrix(page, flow) {
  for (const route of flow.routes) {
    const result = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/${flow.api}/${flow.id}/runs-legacy`, {
        data: { input: flow.directInput(route.input) },
      }),
      `${flow.label} direct ${route.key} branch`,
    )
    assert(result.status === 'SUCCEEDED', `${flow.label}/${route.key} must succeed, got ${result.status}`)
    assert(
      String(result.output?.final || '').includes(route.expected),
      `${flow.label}/${route.key} output must contain ${route.expected}, got ${JSON.stringify(result.output)}`,
    )
    const messageNodeKey = route.key === 'default' ? 'default_message' : `${route.key}_message`
    const nodeResult = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/${flow.api}/${flow.id}/nodes/${messageNodeKey}/runs`, {
        data: { input: flow.directInput(route.input) },
      }),
      `${flow.label} selected ${route.key} message node`,
    )
    const eventTypes = (nodeResult.output?.events || []).map((event) => event.type)
    assert(eventTypes.includes('message_delta'), `${flow.label}/${route.key} selected node must emit message_delta, got ${eventTypes.join(',')}`)
    assert(eventTypes.includes('message_done'), `${flow.label}/${route.key} selected node must emit message_done, got ${eventTypes.join(',')}`)
  }
}

async function configureAndPersistRoute(page, flow) {
  const router = page.locator('.vue-flow__node[data-id="router"]')
  await router.waitFor({ state: 'visible', timeout: 10000 })
  await router.click({ force: true })
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  const section = panel.getByTestId('config-section-条件分支')
  const collapsed = section.locator('.config-section-toggle[aria-expanded="false"]')
  if (await collapsed.count()) await collapsed.click()
  const firstBranchTitle = panel.getByTestId('condition-branch-title').first()
  await firstBranchTitle.click()
  const branchName = panel.getByLabel('分支名称', { exact: true })
  await branchName.fill('退款浏览器配置')
  await branchName.press('Enter')

  const saveResponse = page.waitForResponse((candidate) =>
    candidate.url().includes(`/api/v1/${flow.api}/${flow.id}`) && candidate.request().method() === 'PUT',
  )
  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await unwrap(await saveResponse, `${flow.label} browser save`)
  const persisted = await unwrap(await page.request.get(`${baseUrl}/api/v1/${flow.api}/${flow.id}`), `${flow.label} reload`)
  const routerNode = persisted.nodes.find((node) => node.nodeKey === 'router')
  assert(routerNode?.config?.conditionBranches?.[0]?.name === '退款浏览器配置', `${flow.label} browser configuration must persist`)
}

async function waitForText(locator, expected, label) {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    const text = await locator.innerText().catch(() => '')
    if (text.includes(expected)) return text
    await locator.page().waitForTimeout(250)
  }
  throw new Error(`${label} did not contain ${expected}`)
}

async function runBrowserBranchMatrix(page, flow) {
  await page.locator('.canvas-actions').getByRole('button', { name: flow.label === 'chatflow' ? '对话试运行' : '试运行', exact: true }).click()
  const panel = page.getByTestId('test-run-panel')
  await panel.waitFor({ state: 'visible', timeout: 10000 })

  for (const route of flow.routes) {
    if (flow.label === 'chatflow') {
      await panel.getByPlaceholder('发送消息', { exact: true }).fill(route.input)
      await panel.getByRole('button', { name: '发送消息', exact: true }).click()
      const assistant = panel.getByTestId('chatflow-assistant-message').last()
      await assistant.waitFor({ state: 'visible', timeout: 20000 })
      await waitForText(assistant, route.expected, `${flow.label}/${route.key} browser result`)
    } else {
      await panel.getByPlaceholder('输入 userMessage', { exact: true }).fill(route.input)
      await panel.getByRole('button', { name: '运行', exact: true }).click()
      const output = panel.getByTestId('workflow-run-output')
      await output.waitFor({ state: 'visible', timeout: 20000 })
      await waitForText(output, route.expected, `${flow.label}/${route.key} browser result`)
    }
  }
}

async function verifyBrowserDebugAndPublish(page, flow) {
  await page.locator('.canvas-actions').getByRole('button', { name: '调试详情', exact: true }).click()
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.waitFor({ state: 'visible', timeout: 15000 })
  const debugTab = dock.getByRole('button', { name: '调试', exact: true })
  await debugTab.click()

  if (flow.label === 'chatflow') {
    const summary = dock.getByTestId('chatflow-run-summary')
    await summary.waitFor({ state: 'visible', timeout: 15000 })
    await waitForText(summary, 'SUCCEEDED', `${flow.label} debug summary`)
    const streamPreview = dock.getByTestId('chatflow-debug-stream-preview')
    await streamPreview.waitFor({ state: 'visible', timeout: 15000 })
    await waitForText(streamPreview, flow.routes.at(-1).expected, `${flow.label} debug stream preview`)
  } else {
    const detail = dock.getByTestId('workflow-run-debug-detail')
    await detail.waitFor({ state: 'visible', timeout: 15000 })
    await waitForText(detail, 'SUCCEEDED', `${flow.label} debug detail`)
    await waitForText(detail, flow.routes.at(-1).expected, `${flow.label} debug output`)
  }

  await page.locator('.canvas-actions').getByRole('button', { name: '发布', exact: true }).click()
  const publishDialog = page.getByTestId('workflow-publish-dialog')
  await publishDialog.waitFor({ state: 'visible', timeout: 10000 })
  const publishResponse = page.waitForResponse((candidate) =>
    candidate.url().includes(`/api/v1/${flow.api}/${flow.id}/publish`) && candidate.request().method() === 'POST',
  )
  await publishDialog.getByRole('button', { name: '确认发布', exact: true }).click()
  const published = await unwrap(await publishResponse, `${flow.label} browser publish`)
  const versions = publishDialog.getByTestId('workflow-version-list')
  const row = versions.locator('.version-row').filter({ hasText: `v${published.version}` }).first()
  await row.waitFor({ state: 'visible', timeout: 10000 })
  await row.getByTestId('workflow-version-run').click()
  const targetedResult = publishDialog.locator('.targeted-published-run-result')
  await targetedResult.waitFor({ state: 'visible', timeout: 15000 })
  const targetedText = await targetedResult.innerText()
  assert(targetedText.includes('SUCCEEDED'), `${flow.label} published invocation must succeed, got ${targetedText}`)
  assert(targetedText.includes(`versionId ${published.id}`), `${flow.label} published invocation must target selected version, got ${targetedText}`)
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

if (screenshotDir) await mkdir(screenshotDir, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1600, height: 960 } })
const created = []

try {
  const stamp = Date.now()
  for (const template of flowTemplates) {
    const fixture = fixturePayload(template, stamp)
    const createdFlow = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/${template.api}`, { data: fixture.payload }),
      `create ${template.label}`,
    )
    const flow = { ...template, ...fixture, id: createdFlow.id }
    created.push(flow)

    await verifyDirectBranchMatrix(page, flow)
    await page.goto(`${baseUrl}/${flow.path}/${flow.id}/canvas`, { waitUntil: 'networkidle' })
    await configureAndPersistRoute(page, flow)
    await runBrowserBranchMatrix(page, flow)
    await verifyBrowserDebugAndPublish(page, flow)
    if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/${flow.label}-lifecycle.png`, fullPage: true })
  }
  console.log(`PASS workflow/chatflow deterministic configuration-debug-publish-invoke lifecycle e2e ${JSON.stringify(created.map((flow) => ({ label: flow.label, api: flow.api, id: flow.id })))}`)
} finally {
  try {
    if (!keepFixtures) await cleanupFlows(page, created)
  } finally {
    await browser.close()
  }
}
