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

async function waitForPanelSettled(page) {
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  }))
}

async function createChatflow(page) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Model Selector Compact ${Date.now()}`,
        description: 'model selector compact row e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 160, y: 160 } } } },
          { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { prompt: 'echo {{start.USER_INPUT}}', outputVariable: 'answer', ui: { position: { x: 520, y: 160 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { output: '{{llm_1.answer}}', ui: { position: { x: 900, y: 160 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create chatflow',
  )
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const chatflow = await createChatflow(page)
  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByTestId('llm-model-section').waitFor({ state: 'visible', timeout: 5000 })
  await waitForPanelSettled(page)
  await panel.getByTestId('llm-model-display').click({ force: true })
  const picker = panel.getByTestId('llm-model-selector')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  assert(
    await picker.locator('.model-provider-group > strong').count() === 0,
    'Model picker should not render provider group headings because each row already carries the provider tag',
  )
  assert(
    await picker.locator('[data-testid="llm-model-option"]').count() > 0,
    'Model picker should render compact model rows',
  )
  assert(
    await picker.locator('[data-testid="llm-model-provider-tag"]').count() > 0,
    'Model picker should show provider tags inside model rows',
  )
  assert(
    await picker.locator('[data-testid="llm-model-provider-icon"]').count() > 0,
    'Model picker should show provider icons on the left of model rows',
  )
  assert(
    await picker.locator('[data-testid="llm-model-description"]').count() > 0,
    'Model picker should render a second-line model description',
  )
  const firstRowLayout = await picker.locator('[data-testid="llm-model-option"]').first().evaluate((row) => {
    const box = row.getBoundingClientRect()
    const icon = row.querySelector('[data-testid="llm-model-provider-icon"]')?.getBoundingClientRect()
    const name = row.querySelector('.model-option-name')?.getBoundingClientRect()
    const description = row.querySelector('[data-testid="llm-model-description"]')?.getBoundingClientRect()
    return {
      rowLeft: box.left,
      iconLeft: icon?.left ?? 0,
      iconWidth: icon?.width ?? 0,
      nameLeft: name?.left ?? 0,
      descriptionLeft: description?.left ?? 0,
      descriptionTop: description?.top ?? 0,
      nameBottom: name?.bottom ?? 0,
    }
  })
  assert(
    firstRowLayout.iconLeft < firstRowLayout.nameLeft
      && Math.abs(firstRowLayout.descriptionLeft - firstRowLayout.nameLeft) <= 1
      && firstRowLayout.descriptionTop > firstRowLayout.nameBottom,
    `Model row should be Coze-like left icon with two left-aligned text lines, got ${JSON.stringify(firstRowLayout)}`,
  )
  const tagTexts = await picker.locator('[data-testid="llm-model-provider-tag"]').evaluateAll((tags) =>
    tags.map((tag) => tag.textContent?.trim() || ''),
  )
  assert(
    tagTexts.every((tag) => /^[A-Z_]+$/.test(tag)),
    `Model picker provider tags should use compact provider type labels, got ${JSON.stringify(tagTexts.slice(0, 10))}`,
  )
  const allRowsText = await picker.locator('[data-testid="llm-model-option"]').evaluateAll((rows) =>
    rows.map((row) => row.textContent?.trim() || ''),
  )
  assert(
    allRowsText.length <= 3,
    `Model picker should keep only qwen/deepseek/mimo entries, got ${allRowsText.length}: ${JSON.stringify(allRowsText.slice(0, 10))}`,
  )
  assert(
    allRowsText.every((row) => /qwen|deepseek|mimo|xiaomi/i.test(row)),
    `Model picker should not show polluted test models, got ${JSON.stringify(allRowsText)}`,
  )
  assert(
    allRowsText.every((row) => !/gpt-4o|bad-model|probe-model|agent-call-model/i.test(row)),
    `Model picker should hide historical garbage model data, got ${JSON.stringify(allRowsText)}`,
  )
  const providerIconKeys = await picker.locator('[data-testid="llm-model-provider-icon"]').evaluateAll((icons) =>
    icons.map((icon) => icon.getAttribute('data-provider-icon') || ''),
  )
  const providerLogoCount = await picker.locator('[data-testid="llm-model-provider-icon"] img').count()
  assert(
    providerIconKeys.every((key) => ['openai', 'anthropic', 'gemini', 'azure', 'ollama', 'compatible'].includes(key)),
    `Model picker should use provider protocol logo keys instead of model-family keys, got ${JSON.stringify(providerIconKeys)}`,
  )
  assert(
    providerLogoCount === providerIconKeys.length,
    `Model picker should render local provider protocol logo images for every visible model, got ${providerLogoCount}/${providerIconKeys.length}`,
  )

  const search = picker.getByPlaceholder('搜索模型或供应商')
  await search.fill('gpt')
  await picker.getByRole('button', { name: '搜索模型', exact: true }).click()

  const text = await picker.innerText()
  assert(!text.toLowerCase().includes('gpt'), `Filtered model list should not include gpt garbage options, got ${text}`)
  assert(!text.includes('已启用'), `Model rows should not repeat enabled status text, got ${text}`)
  assert(!text.includes('xiaomi/mimo-v2-flash'), `Filtered model list should hide non-matching models, got ${text}`)

  await search.fill('mimo')
  await picker.getByRole('button', { name: '搜索模型', exact: true }).click()
  const filteredText = await picker.innerText()
  assert(/mimo|小米/i.test(filteredText), `Filtered model list should include a mimo family option, got ${filteredText}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow model selector search 028')
} finally {
  await browser.close()
}
