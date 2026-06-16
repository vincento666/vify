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
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'load' })
  await page.locator('.coze-node.node-end').click()

  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })

  const editor = panel.getByTestId('config-section-回答内容').getByTestId('end-answer-content-editor')
  await editor.waitFor({ state: 'visible', timeout: 5000 })

  const responseInput = editor.locator('textarea[aria-label="回答内容"]')
  await responseInput.fill('')
  await responseInput.focus()
  await responseInput.pressSequentially('{')

  const picker = editor.getByTestId('variable-picker')
  await picker.waitFor({ state: 'visible', timeout: 5000 })

  const option = picker.getByTestId('variable-option').first()
  await option.waitFor({ state: 'visible', timeout: 5000 })

  const metrics = await option.evaluate((element) => {
    const optionRect = element.getBoundingClientRect()
    const name = element.querySelector('.variable-option-main strong')
    const badge = element.querySelector('.variable-type-badge')
    const nameRect = name?.getBoundingClientRect()
    const badgeRect = badge?.getBoundingClientRect()
    const nameStyle = name ? window.getComputedStyle(name) : null
    return {
      optionWidth: optionRect.width,
      nameText: name?.textContent?.trim() || '',
      nameWidth: nameRect?.width || 0,
      nameClientWidth: name?.clientWidth || 0,
      nameScrollWidth: name?.scrollWidth || 0,
      nameTextOverflow: nameStyle?.textOverflow || '',
      nameOverflow: nameStyle?.overflow || '',
      badgeText: badge?.textContent?.trim() || '',
      badgeWidth: badgeRect?.width || 0,
      badgeLeft: badgeRect?.left || 0,
      nameRight: nameRect?.right || 0,
    }
  })

  assert(metrics.nameText.length > 0, `Expected a visible inline variable name, got ${JSON.stringify(metrics)}`)
  assert(metrics.badgeText === 'String', `Expected full type label String, got ${JSON.stringify(metrics)}`)
  assert(metrics.nameTextOverflow !== 'ellipsis', `Inline variable names should not use ellipsis styling: ${JSON.stringify(metrics)}`)
  assert(metrics.nameScrollWidth <= metrics.nameClientWidth + 1, `Variable name should not be ellipsized: ${JSON.stringify(metrics)}`)
  assert(metrics.badgeWidth <= 5 * 16, `Variable type badge should be compact, got ${JSON.stringify(metrics)}`)
  assert(metrics.badgeLeft >= metrics.nameRight + 0.25 * 16, `Type badge should sit after the variable name, got ${JSON.stringify(metrics)}`)

  const llmFlow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Inline LLM Variable ${Date.now()}`,
        description: 'llm node local variable insertion regression',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 160, y: 240 } } } },
          {
            nodeKey: 'llm_1',
            type: 'LLM',
            name: '大模型',
            config: {
              inputParameters: [{ name: 'input_1', type: 'string', valueMode: 'reference', value: '{{start.sys.query}}' }],
              systemPrompt: '',
              outputVariable: 'answer',
              ui: { position: { x: 520, y: 240 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { output: '{{llm_1.answer}}', ui: { position: { x: 880, y: 240 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create llm inline variable chatflow',
  )
  await page.goto(`${baseUrl}/chatflows/${llmFlow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()

  const llmSystemSection = panel.getByTestId('config-section-系统提示词')
  await llmSystemSection.waitFor({ state: 'visible', timeout: 5000 })
  const systemPrompt = llmSystemSection.locator('textarea')
  await systemPrompt.fill('')
  await systemPrompt.focus()
  await systemPrompt.pressSequentially('{')

  const llmPicker = llmSystemSection.getByTestId('variable-picker')
  await llmPicker.waitFor({ state: 'visible', timeout: 5000 })
  const llmOption = llmPicker.getByTestId('variable-option').filter({ hasText: 'input_1' }).first()
  await llmOption.waitFor({ state: 'visible', timeout: 5000 })

  const llmMetrics = await llmOption.evaluate((element) => {
    const optionRect = element.getBoundingClientRect()
    const name = element.querySelector('.variable-option-main strong')
    const badge = element.querySelector('.variable-type-badge')
    const main = element.querySelector('.variable-option-main')
    const nameRect = name?.getBoundingClientRect()
    const badgeRect = badge?.getBoundingClientRect()
    const mainRect = main?.getBoundingClientRect()
    const nameStyle = name ? window.getComputedStyle(name) : null
    const style = badge ? window.getComputedStyle(badge) : null
    return {
      optionWidth: optionRect.width,
      mainWidth: mainRect?.width || 0,
      nameText: name?.textContent?.trim() || '',
      nameWidth: nameRect?.width || 0,
      nameClientWidth: name?.clientWidth || 0,
      nameScrollWidth: name?.scrollWidth || 0,
      nameTextOverflow: nameStyle?.textOverflow || '',
      nameOverflow: nameStyle?.overflow || '',
      badgeText: badge?.textContent?.trim() || '',
      badgeWidth: badgeRect?.width || 0,
      badgeLeft: badgeRect?.left || 0,
      nameRight: nameRect?.right || 0,
      badgeDisplay: style?.display || '',
    }
  })

  assert(llmMetrics.nameText === 'input_1', `Expected LLM local variable name input_1, got ${JSON.stringify(llmMetrics)}`)
  assert(llmMetrics.badgeText === 'String', `Expected full type label String, got ${JSON.stringify(llmMetrics)}`)
  assert(llmMetrics.nameTextOverflow !== 'ellipsis', `LLM inline variable names should not use ellipsis styling: ${JSON.stringify(llmMetrics)}`)
  assert(llmMetrics.nameScrollWidth <= llmMetrics.nameClientWidth + 1, `LLM variable name should not be ellipsized: ${JSON.stringify(llmMetrics)}`)
  assert(llmMetrics.badgeWidth <= 5 * 16, `LLM variable type badge should be compact, got ${JSON.stringify(llmMetrics)}`)
  assert(llmMetrics.mainWidth <= llmMetrics.nameWidth + llmMetrics.badgeWidth + 1.25 * 16, `Inline option main area should shrink to content, got ${JSON.stringify(llmMetrics)}`)

  await llmOption.click()
  const llmInsertedValue = await systemPrompt.inputValue()
  assert(llmInsertedValue === '{{input_1}}', `Expected LLM inline variable to insert local reference only, got ${llmInsertedValue}`)
  assert(!llmInsertedValue.includes('llm_1.'), `LLM inline variable must not include node prefix, got ${llmInsertedValue}`)

  const messageFlow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Inline Message Variable ${Date.now()}`,
        description: 'message node local variable insertion regression',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 160, y: 240 } } } },
          {
            nodeKey: 'message_1',
            type: 'MESSAGE',
            name: '消息',
            config: {
              inputParameters: [{ name: 'message_input', type: 'string', valueMode: 'reference', value: '{{start.sys.query}}' }],
              content: '',
              outputVariable: 'output',
              ui: { position: { x: 520, y: 240 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { output: '{{message_1.output}}', ui: { position: { x: 880, y: 240 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
          { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create message inline variable chatflow',
  )
  await page.goto(`${baseUrl}/chatflows/${messageFlow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="message_1"]').click()

  const messageSection = panel.getByTestId('config-section-发送消息')
  await messageSection.waitFor({ state: 'visible', timeout: 5000 })
  const messageTextarea = messageSection.locator('textarea').first()
  await messageTextarea.fill('')
  await messageTextarea.focus()
  await messageTextarea.pressSequentially('{')

  const messagePicker = messageSection.getByTestId('variable-picker')
  await messagePicker.waitFor({ state: 'visible', timeout: 5000 })
  const messageOption = messagePicker.getByTestId('variable-option').filter({ hasText: 'message_input' }).first()
  await messageOption.waitFor({ state: 'visible', timeout: 5000 })
  await messageOption.click()
  const messageInsertedValue = await messageTextarea.inputValue()
  assert(messageInsertedValue === '{{message_input}}', `Expected message inline variable to insert local reference only, got ${messageInsertedValue}`)
  assert(!messageInsertedValue.includes('message_1.'), `Message inline variable must not include node prefix, got ${messageInsertedValue}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow inline variable option layout and local insertion')
} finally {
  await browser.close()
}
