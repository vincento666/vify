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
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `027.1 Start Defaults ${Date.now()}`,
        description: 'start defaults hardening e2e',
        nodes: [
          {
            nodeKey: 'start',
            type: 'START',
            name: '开始',
            config: {
              outputVariables: ['sys.query', 'sys.conversation_id', 'sys.user_id', 'sys.channel', 'input'],
              ui: { position: { x: 140, y: 220 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.sys.query}}', ui: { position: { x: 680, y: 220 } } } },
        ],
        edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
      },
    }),
    'create 027.1 chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="start"]').click()
  const panel = page.getByTestId('node-config-panel')
  const editor = panel.getByTestId('start-variable-editor')
  await editor.waitFor({ state: 'visible', timeout: 5000 })

  const rows = editor.getByTestId('start-variable-row')
  const firstDefault = rows.first()
  await firstDefault.waitFor({ state: 'visible', timeout: 5000 })
  assert(await firstDefault.getByLabel('开始变量名').inputValue() === 'sys.query', 'Expected first default variable to be sys.query')
  assert(await firstDefault.getByLabel('开始变量名').isDisabled(), 'Default chatflow message variable name must be locked')
  assert(await firstDefault.getByLabel('开始变量类型').isDisabled(), 'Default chatflow message variable type must be locked')
  assert(await firstDefault.getByLabel('开始变量必填').isDisabled(), 'Default chatflow message variable required toggle must be locked')
  assert(!(await firstDefault.getByLabel('开始变量必填').isChecked()), 'Default chatflow message variable must not be required')
  assert(await firstDefault.getByRole('button', { name: '删除开始变量', exact: true }).isDisabled(), 'Default chatflow message variable must not be deletable')

  await editor.getByRole('button', { name: '添加开始变量', exact: true }).click()
  const customRow = rows.last()
  await customRow.getByLabel('开始变量名').fill('ticket_id')
  assert(!(await customRow.getByLabel('开始变量名').isDisabled()), 'Custom Start variable name must stay editable')
  assert(!(await customRow.getByLabel('开始变量必填').isDisabled()), 'Custom Start variable required toggle must stay editable')
  assert(!(await customRow.getByRole('button', { name: '删除开始变量', exact: true }).isDisabled()), 'Custom Start variable must stay deletable')

  await page.getByRole('button', { name: '对话试运行', exact: true }).click()
  const runPanel = page.getByTestId('test-run-panel')
  await runPanel.getByTestId('chatflow-run-message-input').waitFor({ state: 'visible', timeout: 5000 })
  const runPanelText = await runPanel.innerText()
  assert(!runPanelText.includes('sys.query'), 'Chatflow default message input must not appear as an extra trial field')
  assert(!runPanelText.includes('input'), 'Chatflow input payload default must not appear as an extra trial field')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS 027.1 start default inputs e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
