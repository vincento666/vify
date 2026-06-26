import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Chatflow Probe ${Date.now()}`

const responses = []
page.on('response', async (res) => {
  const url = res.url()
  if (/\/v1\/(chatflows|workflows|runtime-runs)/.test(url)) {
    try {
      const ct = res.headers()['content-type'] || ''
      if (ct.includes('application/json')) {
        const body = await res.text()
        responses.push({ method: res.request().method(), url, status: res.status(), body: body.slice(0, 4000) })
      } else {
        responses.push({ method: res.request().method(), url, status: res.status(), ct })
      }
    } catch (e) {
      responses.push({ method: res.request().method(), url, status: res.status(), err: String(e) })
    }
  }
})

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Chatflow 名称').fill(name)
  await page.locator('.coze-node', { hasText: '结束' }).click()
  const configPanel = page.locator('[data-testid="node-config-panel"]')
  await configPanel.waitFor({ state: 'visible', timeout: 5000 })
  await configPanel
    .getByPlaceholder('返回给调用方的文本，可使用变量引用')
    .fill('机器人收到 {{sys.query}} via {{sys.channel}} for {{global.brand}}/{{global.locale}}')

  await page.getByRole('button', { name: '对话试运行' }).click()
  const testPanel = page.locator('[data-testid="test-run-panel"]')
  await testPanel.waitFor({ state: 'visible', timeout: 5000 })
  await testPanel.getByTestId('chatflow-run-fields-toggle').click()
  await testPanel.getByPlaceholder('发送消息').fill('查订单')
  await testPanel.getByPlaceholder('conversation_id').fill('conv-e2e')
  await testPanel.getByPlaceholder('user_id').fill('user-e2e')
  await testPanel.getByRole('button', { name: '发送消息', exact: true }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await testPanel.getByTestId('chatflow-assistant-message').waitFor({ state: 'visible', timeout: 10000 })

  // Sample innerText immediately (race) and after polling
  const immediateInnerText = await testPanel.getByTestId('chatflow-assistant-message').innerText()
  let polledInnerText = immediateInnerText
  const deadline = Date.now() + 8000
  while (!polledInnerText.includes('机器人收到') && Date.now() < deadline) {
    await page.waitForTimeout(100)
    polledInnerText = await testPanel.getByTestId('chatflow-assistant-message').innerText()
  }
  const finalLoadingCount = await testPanel.getByTestId('chatflow-assistant-loading').count()
  const finalAssistantCount = await testPanel.getByTestId('chatflow-assistant-message').count()
  const bubbleClasses = await testPanel.getByTestId('chatflow-assistant-message').evaluateAll((els) => els.map((el) => el.className))
  const bubbleInnerHTML = await testPanel.getByTestId('chatflow-assistant-message').evaluateAll((els) => els.map((el) => el.innerHTML))

  console.log('IMMEDIATE_INNER_TEXT:', JSON.stringify(immediateInnerText))
  console.log('POLLED_INNER_TEXT:', JSON.stringify(polledInnerText))
  console.log('FINAL_LOADING_COUNT:', finalLoadingCount)
  console.log('FINAL_ASSISTANT_COUNT:', finalAssistantCount)
  console.log('BUBBLE_CLASSES:', JSON.stringify(bubbleClasses))
  console.log('BUBBLE_INNERHTML:', JSON.stringify(bubbleInnerHTML))
  console.log('RESPONSES:', JSON.stringify(responses, null, 2))
} finally {
  await browser.close()
}
