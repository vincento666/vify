import { chromium } from 'playwright'
import { waitForRuntimeResult } from './runtime-run-helpers.mjs'

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

function transformNodes(startVars = ['USER_INPUT']) {
  return [
    {
      nodeKey: 'start',
      type: 'START',
      name: '开始',
      config: { outputVariables: startVars, ui: { position: { x: 120, y: 120 } } },
    },
    {
      nodeKey: 'code_1',
      type: 'CODE',
      name: '代码',
      config: {
        language: 'python',
        code: "result = {'full_name': inputs.get('first', '') + ' ' + inputs.get('last', ''), 'score': int(inputs.get('score', 0))}",
        outputParameters: [
          { name: 'full_name', type: 'string' },
          { name: 'score', type: 'number' },
        ],
        ui: { position: { x: 420, y: 100 } },
      },
    },
    {
      nodeKey: 'text_process_1',
      type: 'TEXT_PROCESS',
      name: '文本处理',
      config: {
        operation: 'format_template',
        template: '{"name":"{{code_1.full_name}}","score":{{code_1.score}},"grade":"A"}',
        outputVariable: 'jsonText',
        outputParameters: [{ name: 'jsonText', type: 'string' }],
        ui: { position: { x: 720, y: 100 } },
      },
    },
    {
      nodeKey: 'json_parse_1',
      type: 'JSON_PARSE',
      name: 'JSON 解析',
      config: {
        source: '{{text_process_1.jsonText}}',
        outputVariable: 'parsed',
        fieldMap: [
          { name: 'name', path: '$.name' },
          { name: 'score', path: '$.score' },
          { name: 'grade', path: '$.grade' },
        ],
        outputParameters: [{ name: 'parsed', type: 'object' }],
        ui: { position: { x: 1020, y: 100 } },
      },
    },
    {
      nodeKey: 'end',
      type: 'END',
      name: '结束',
      config: {
        outputVariable: 'final',
        output: '{{json_parse_1.name}}/{{json_parse_1.score}}/{{json_parse_1.grade}}',
        ui: { position: { x: 1320, y: 120 } },
      },
    },
  ]
}

const edges = [
  { sourceNodeKey: 'start', targetNodeKey: 'code_1', condition: null },
  { sourceNodeKey: 'code_1', targetNodeKey: 'text_process_1', condition: null },
  { sourceNodeKey: 'text_process_1', targetNodeKey: 'json_parse_1', condition: null },
  { sourceNodeKey: 'json_parse_1', targetNodeKey: 'end', condition: null },
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `015.1 Transform Workflow ${Date.now()}`,
        description: 'CODE/TEXT_PROCESS/JSON_PARSE e2e',
        nodes: transformNodes(['first', 'last', 'score']),
        edges,
      },
    }),
    'create transform workflow',
  )
  const workflowStarted = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
      data: { input: { first: 'Ada', last: 'Lovelace', score: 97 } },
    }),
    'run transform workflow',
  )
  const workflowRun = await waitForRuntimeResult(page, baseUrl, workflowStarted, 'transform workflow')
  assert(workflowRun.output.final === 'Ada Lovelace/97/A', `Unexpected workflow output ${JSON.stringify(workflowRun.output)}`)

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-code').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-text_process').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-json_parse').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-code').click()
  const codePanel = page.locator('[data-testid="node-config-panel"]')
  await codePanel.waitFor({ state: 'visible', timeout: 5000 })
  await codePanel.getByText('代码配置', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  const codeEditor = codePanel.locator('[data-testid="code-editor-field"]')
  assert(await codeEditor.count() === 1, 'Expected Code node to render a dedicated code editor field')
  await codeEditor.getByText('Python', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  await codePanel.getByText('插入基础模板', { exact: true }).click()
  const pythonTemplate = await codeEditor.locator('textarea').inputValue()
  assert(pythonTemplate.includes('def main(args):'), 'Expected Python template insertion to use a main(args) entry function')
  assert(pythonTemplate.includes("args.get('input'"), 'Expected Python template to read node inputs through args.get')
  await codePanel.getByRole('button', { name: '关闭配置', exact: true }).click()
  await codePanel.waitFor({ state: 'hidden', timeout: 5000 })

  await page.locator('.coze-node.node-json_parse').click()
  const configPanel = page.locator('[data-testid="node-config-panel"]')
  await configPanel.waitFor({ state: 'visible', timeout: 5000 })
  const configText = await configPanel.innerText()
  assert(configText.includes('JSON 来源'), 'Expected JSON_PARSE source field in config panel')
  assert(configText.includes('字段映射'), 'Expected JSON_PARSE field map field in config panel')
  assert(await configPanel.locator('[data-testid="json-field-mapping-editor"]').count() === 1, 'Expected structured JSON field mapping editor')
  assert(await configPanel.locator('[data-testid="json-field-mapping-row"]').count() === 3, 'Expected JSON field mapping rows')
  assert(await configPanel.locator('[data-testid="json-field-mapping-editor"] textarea').count() === 0, 'Expected JSON mapping basic editor not to use raw textarea')

  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `015.1 Transform Chatflow ${Date.now()}`,
        description: 'chatflow transform e2e',
        nodes: transformNodes(['first', 'last', 'score', 'sys.query', 'sys.conversation_id', 'sys.user_id', 'sys.channel']),
        edges,
      },
    }),
    'create transform chatflow',
  )
  const chatflowRun = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs-legacy`, {
      data: { input: { first: 'Grace', last: 'Hopper', score: 100, 'sys.query': 'transform' } },
    }),
    'run transform chatflow',
  )
  assert(chatflowRun.output.final === 'Grace Hopper/100/A', `Unexpected chatflow output ${JSON.stringify(chatflowRun.output)}`)

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-code').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-text_process').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-json_parse').waitFor({ state: 'visible', timeout: 10000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow/chatflow transform nodes e2e')
} finally {
  await browser.close()
}
