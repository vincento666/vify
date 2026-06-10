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
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `Intent Panel Polish ${Date.now()}`,
        description: 'intent panel polish e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 220 } } } },
          {
            nodeKey: 'intent_1',
            type: 'INTENT_RECOGNITION',
            name: '意图识别',
            config: {
              inputSource: '{{start.USER_INPUT}}',
              intents: [
                { key: 'after_sale', name: '售后', description: '售后问题', examples: ['我要退货', '我要换货'], branch: 'after_sale' },
                { key: 'invoice', name: '发票', description: '发票开具', examples: ['我要开发票'], branch: 'invoice' },
              ],
              ui: { position: { x: 500, y: 180 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { output: '{{intent_1.intent}}', outputVariable: 'final', ui: { position: { x: 900, y: 220 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'intent_1', condition: null },
          { sourceNodeKey: 'intent_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create intent workflow',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="intent_1"]').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })

  const titleMetrics = await panel.locator('.config-title-heading, .config-header h3').first().evaluate((element) => {
    const style = getComputedStyle(element)
    return { text: element.textContent?.trim(), fontSize: Number.parseFloat(style.fontSize) }
  })
  assert(titleMetrics.text === '意图识别', `Config header should only show node title, got ${JSON.stringify(titleMetrics)}`)
  assert(titleMetrics.fontSize >= 20, `Config header title should be prominent, got ${JSON.stringify(titleMetrics)}`)
  const headerText = await panel.locator('.config-header').innerText()
  assert(!headerText.includes('用于用户输入的意图识别'), `Config header should not render node description, got ${headerText}`)

  const editor = panel.getByTestId('intent-row-editor')
  await editor.waitFor({ state: 'visible', timeout: 5000 })
  const rows = editor.getByTestId('intent-row')
  assert(await rows.count() === 2, 'Expected two intent rows')
  const first = rows.first()
  assert(await first.getByRole('button', { name: '拖拽意图排序', exact: true }).count() === 1, 'Intent row should expose a drag handle')
  const layout = await first.evaluate((element) => {
    const style = getComputedStyle(element)
    const areas = style.gridTemplateAreas
    const columns = style.gridTemplateColumns
    const textarea = element.querySelector('textarea')
    const textareaStyle = textarea ? getComputedStyle(textarea) : null
    return {
      areas,
      columns,
      textareaResize: textareaStyle?.resize,
      textareaHeight: textareaStyle?.height,
      rowHeight: element.getBoundingClientRect().height,
    }
  })
  assert(layout.areas.includes('name description') && layout.areas.includes('examples examples'), `Intent row should use two-line grid areas, got ${JSON.stringify(layout)}`)
  assert(layout.textareaResize === 'none', `Intent examples textarea must not be manually resizable, got ${JSON.stringify(layout)}`)

  await first.getByRole('textbox', { name: '意图示例', exact: true }).fill('x'.repeat(320))
  const exampleValue = await first.getByRole('textbox', { name: '意图示例', exact: true }).inputValue()
  assert(exampleValue.length <= 300, `Intent examples should be capped at 300 chars, got ${exampleValue.length}`)

  const handles = editor.getByRole('button', { name: '拖拽意图排序', exact: true })
  const firstHandleBox = await handles.first().boundingBox()
  const secondHandleBox = await handles.nth(1).boundingBox()
  assert(firstHandleBox && secondHandleBox, 'Expected drag handle geometry')
  await page.mouse.move(firstHandleBox.x + firstHandleBox.width / 2, firstHandleBox.y + firstHandleBox.height / 2)
  await page.mouse.down()
  await page.mouse.move(secondHandleBox.x + secondHandleBox.width / 2, secondHandleBox.y + secondHandleBox.height / 2 + 12, { steps: 8 })
  await page.mouse.up()
  await page.waitForTimeout(200)
  const firstNameAfterDrag = await rows.first().getByRole('textbox', { name: '意图名称', exact: true }).inputValue()
  assert(firstNameAfterDrag === '发票', `Dragging intent row should reorder rows, got first=${firstNameAfterDrag}`)

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })
  console.log('PASS workflow intent panel polish e2e')
} finally {
  await browser.close()
}
