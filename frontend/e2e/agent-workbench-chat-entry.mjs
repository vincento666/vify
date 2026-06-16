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

async function findEnabledModel(page) {
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      if (String(provider.baseUrl || '').startsWith('mock://')) continue
      for (const model of provider.models ?? []) {
        if (model.enabled) return model.id
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  throw new Error('No enabled model found for Agent chat entry e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const marker = `CHAT_ENTRY_${Date.now()}`
  const openingMessage = `你好，我是 ${marker} 的售后助手。`
  const suggestedQuestion = `Return exactly this marker: ${marker}`
  const agent = await unwrap(await page.request.post(`${baseUrl}/api/v1/agents`, {
    data: {
      name: `Chat Entry Agent ${marker}`,
      description: 'chat entry e2e',
      systemPrompt: "Follow the user's marker instructions exactly.",
      modelConfigId,
      temperature: 0,
      maxTokens: 64,
      maxContextTurns: 2,
      openingMessage,
      suggestedQuestions: [suggestedQuestion, '查订单状态'],
      toolIds: [],
    },
  }), 'create chat entry agent')

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'networkidle' })
  const preview = page.getByTestId('agent-workbench-preview')
  await preview.getByText(openingMessage, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  const starterLayout = await preview.evaluate(() => {
    const body = document.querySelector('[data-testid="agent-workbench-preview"] .preview-body')?.getBoundingClientRect()
    const opening = document.querySelector('[data-testid="agent-preview-opening-message"]')?.getBoundingClientRect()
    const openingElement = document.querySelector('[data-testid="agent-preview-opening-message"]')
    const suggestions = document.querySelector('[data-testid="agent-preview-suggested-questions"]')?.getBoundingClientRect()
    const reset = document.querySelector('[data-testid="agent-workbench-preview"] .preview-header [aria-label="重置预览"]')?.getBoundingClientRect()
    const send = document.querySelector('[data-testid="agent-workbench-preview"] .preview-composer-toolbar [aria-label="发送预览消息"]')?.getBoundingClientRect()
    const composer = document.querySelector('[data-testid="agent-workbench-preview"] .preview-composer')?.getBoundingClientRect()
    const composerInput = document.querySelector('[data-testid="agent-workbench-preview"] .preview-composer .el-textarea__inner')
    const composerInputStyle = composerInput ? getComputedStyle(composerInput) : null
    const composerToolbar = document.querySelector('[data-testid="agent-workbench-preview"] .preview-composer-toolbar')
    const composerToolbarStyle = composerToolbar ? getComputedStyle(composerToolbar) : null
    const pillRects = [...document.querySelectorAll('[data-testid="agent-workbench-preview"] .suggestion-pill')]
      .map((pill) => pill.getBoundingClientRect())
      .map((rect) => ({ width: Math.round(rect.width), right: Math.round(rect.right) }))
    return {
      bodyLeft: Math.round(body?.left ?? 0),
      bodyRight: Math.round(body?.right ?? 0),
      bodyBottom: Math.round(body?.bottom ?? 0),
      bodyWidth: Math.round(body?.width ?? 0),
      openingTop: Math.round(opening?.top ?? 0),
      openingWidth: Math.round(opening?.width ?? 0),
      openingClass: openingElement?.className ?? '',
      suggestionsLeft: Math.round(suggestions?.left ?? 0),
      suggestionsRight: Math.round(suggestions?.right ?? 0),
      suggestionsBottom: Math.round(suggestions?.bottom ?? 0),
      pillRects,
      resetTop: Math.round(reset?.top ?? 0),
      sendRight: Math.round(send?.right ?? 0),
      composerRight: Math.round(composer?.right ?? 0),
      inputResize: composerInputStyle?.resize ?? '',
      toolbarBorderTop: composerToolbarStyle?.borderTopWidth ?? '',
    }
  })
  assert(starterLayout.openingTop > 0, `Expected opening message in preview conversation: ${JSON.stringify(starterLayout)}`)
  assert(starterLayout.openingClass.includes('assistant'), `Expected opening message as assistant bubble: ${JSON.stringify(starterLayout)}`)
  assert(starterLayout.openingWidth < starterLayout.bodyWidth - 16, `Expected opening bubble width to fit content: ${JSON.stringify(starterLayout)}`)
  assert(starterLayout.bodyRight - starterLayout.suggestionsRight <= 16, `Expected suggested questions right-bottom aligned: ${JSON.stringify(starterLayout)}`)
  assert(starterLayout.bodyBottom - starterLayout.suggestionsBottom <= 24, `Expected suggested questions bottom aligned: ${JSON.stringify(starterLayout)}`)
  assert(starterLayout.pillRects.every((rect) => rect.width < starterLayout.bodyWidth - 32), `Expected suggested question bubbles to fit content: ${JSON.stringify(starterLayout)}`)
  assert(starterLayout.pillRects.every((rect) => starterLayout.bodyRight - rect.right <= 16), `Expected suggested question bubbles right aligned: ${JSON.stringify(starterLayout)}`)
  assert(starterLayout.resetTop > 0, `Expected reset icon in preview header: ${JSON.stringify(starterLayout)}`)
  assert(starterLayout.composerRight - starterLayout.sendRight <= 12, `Expected send icon right aligned in composer toolbar: ${JSON.stringify(starterLayout)}`)
  assert(starterLayout.inputResize === 'none', `Expected preview textarea resize disabled: ${JSON.stringify(starterLayout)}`)
  assert(starterLayout.toolbarBorderTop === '0px', `Expected composer input/action divider removed: ${JSON.stringify(starterLayout)}`)
  await preview.getByRole('button', { name: suggestedQuestion, exact: true }).click()
  await preview.getByText(marker, { exact: true }).waitFor({ state: 'visible', timeout: 60000 })
  const previewUserBubble = await preview.locator('.preview-message.user').evaluate((element) =>
    getComputedStyle(element).backgroundColor,
  )
  assert(isLightBlue(previewUserBubble), `Workbench preview user bubble should be light blue, got ${previewUserBubble}`)

  await unwrap(await page.request.post(`${baseUrl}/api/v1/chat/sessions`, {
    data: { agentId: agent.id },
  }), 'create chat session')
  await page.goto(`${baseUrl}/chat`, { waitUntil: 'networkidle' })
  await page.locator('.chat-topbar-name', { hasText: `Chat Entry Agent ${marker}` }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText(openingMessage, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: suggestedQuestion, exact: true }).click()
  await page.locator('.messages-wrap .msg-row.assistant .msg-content', { hasText: marker }).waitFor({ state: 'visible', timeout: 60000 })
  const chatUserBubble = await page.locator('.messages-wrap .msg-row.user .msg-bubble').evaluate((element) =>
    getComputedStyle(element).backgroundColor,
  )
  assert(isLightBlue(chatUserBubble), `ChatView user bubble should be light blue, got ${chatUserBubble}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench chat entry e2e')
} finally {
  await browser.close()
}

function isLightBlue(color) {
  const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  if (!match) return false
  const [, red, green, blue] = match.map(Number)
  return red >= 210 && green >= 225 && blue >= 240 && blue >= green
}
