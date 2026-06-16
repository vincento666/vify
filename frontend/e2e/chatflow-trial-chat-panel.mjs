import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const runResponses = []

page.on('response', async (response) => {
  if (response.url().includes('/api/v1/chatflows/') && response.url().includes('/runs')) {
    runResponses.push(response.status())
  }
})

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })

  const toolbar = page.locator('[data-testid="canvas-bottom-toolbar"]')
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })
  assert(await toolbar.getByRole('button', { name: '适应画布', exact: true }).count() === 0, 'Expected fit-view toolbar button removed')

  await page.getByRole('button', { name: '对话试运行', exact: true }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const panelLayer = await page.evaluate(() => {
    const panelEl = document.querySelector('[data-testid="test-run-panel"]')
    const toolbarEl = document.querySelector('[data-testid="canvas-bottom-toolbar"]')
    const zIndex = (element) => Number.parseInt(window.getComputedStyle(element).zIndex || '0', 10) || 0
    return {
      panel: panelEl ? zIndex(panelEl) : 0,
      toolbar: toolbarEl ? zIndex(toolbarEl) : 0,
    }
  })
  assert(
    panelLayer.panel > panelLayer.toolbar,
    `Expected chatflow trial panel to layer above toolbar, got ${JSON.stringify(panelLayer)}`,
  )

  await panel.getByTestId('chatflow-run-chat-window').waitFor({ state: 'visible', timeout: 5000 })
  assert((await panel.getByText('保存本次输入').count()) === 0, 'Expected saved-input checkbox removed')
  assert((await panel.getByRole('button', { name: '开始试运行', exact: true }).count()) === 0, 'Expected form-style run button removed')

  assert(await panel.getByTestId('chatflow-run-fields').count() === 0, 'Expected run fields removed from chat body')
  const settingsButton = panel.getByRole('button', { name: '对话设置', exact: true })
  await settingsButton.waitFor({ state: 'visible', timeout: 5000 })
  assert(await panel.getByPlaceholder('conversation_id').count() === 0, 'Expected run fields hidden until header settings opens')
  await settingsButton.click()
  await panel.getByTestId('chatflow-run-settings-popover').waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByPlaceholder('conversation_id').waitFor({ state: 'visible', timeout: 5000 })
  await settingsButton.click()
  await panel.getByTestId('chatflow-run-settings-popover').waitFor({ state: 'hidden', timeout: 5000 })
  assert(await panel.getByRole('button', { name: '清空对话', exact: true }).count() === 1, 'Expected clear conversation action in header')
  assert(await panel.getByRole('button', { name: '上传文件', exact: true }).count() === 1, 'Expected upload affordance inside composer')
  const composerShell = panel.getByTestId('chatflow-composer-shell')
  const composerEditor = panel.getByTestId('chatflow-composer-editor')
  const composerActions = panel.getByTestId('chatflow-composer-actions')
  await composerShell.waitFor({ state: 'visible', timeout: 5000 })
  await composerEditor.waitFor({ state: 'visible', timeout: 5000 })
  await composerActions.waitFor({ state: 'visible', timeout: 5000 })
  const initialComposerLayout = await composerShell.evaluate((shell) => {
    const editor = shell.querySelector('[data-testid="chatflow-composer-editor"]')
    const actions = shell.querySelector('[data-testid="chatflow-composer-actions"]')
    const input = shell.querySelector('[data-testid="chatflow-run-message-input"] textarea')
      || shell.querySelector('[data-testid="chatflow-run-message-input"]')
    const shellStyle = window.getComputedStyle(shell)
    const editorRect = editor.getBoundingClientRect()
    const actionsRect = actions.getBoundingClientRect()
    const inputRect = input.getBoundingClientRect()
    return {
      shellBorderWidth: shellStyle.borderWidth,
      editorBottom: editorRect.bottom,
      actionsTop: actionsRect.top,
      inputWidth: inputRect.width,
      shellWidth: shell.getBoundingClientRect().width,
    }
  })
  assert(initialComposerLayout.shellBorderWidth !== '0px', `Expected composer shell to own the only border ${JSON.stringify(initialComposerLayout)}`)
  assert(
    initialComposerLayout.editorBottom <= initialComposerLayout.actionsTop + 2,
    `Expected composer actions on a second row below the editor ${JSON.stringify(initialComposerLayout)}`,
  )
  assert(
    initialComposerLayout.inputWidth > initialComposerLayout.shellWidth * 0.84,
    `Expected message input to occupy the full upper row ${JSON.stringify(initialComposerLayout)}`,
  )

  await panel.getByTestId('chatflow-opening-message').waitFor({ state: 'visible', timeout: 5000 })
  const suggestions = panel.getByTestId('chatflow-guide-question')
  assert(await suggestions.count() >= 1, 'Expected suggested questions')
  await suggestions.first().click()

  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await panel.getByTestId('chatflow-user-message').waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByTestId('chatflow-assistant-message').waitFor({ state: 'visible', timeout: 10000 })
  assert(!runResponses.includes(500), `Expected no 500 run response, got ${runResponses.join(',')}`)

  const composer = panel.getByPlaceholder('输入问题，可通过 shift + enter 换行')
  await composer.fill('查退款')
  const composerBox = await composer.evaluate((element) => ({
    scrollHeight: element.scrollHeight,
    clientHeight: element.clientHeight,
    overflowY: window.getComputedStyle(element).overflowY,
  }))
  assert(
    composerBox.scrollHeight <= composerBox.clientHeight + 2 || composerBox.overflowY === 'hidden',
    `Expected single-line composer without visible scrollbar, got ${JSON.stringify(composerBox)}`,
  )
  const shortShellHeight = await composerShell.evaluate((element) => element.getBoundingClientRect().height)
  await composer.fill(Array.from({ length: 12 }, (_, index) => `第${index + 1}行消息内容`).join('\n'))
  const longComposerBox = await composer.evaluate((element) => ({
    scrollHeight: element.scrollHeight,
    clientHeight: element.clientHeight,
    overflowY: window.getComputedStyle(element).overflowY,
  }))
  const longShellHeight = await composerShell.evaluate((element) => element.getBoundingClientRect().height)
  assert(longShellHeight > shortShellHeight + 24, `Expected composer to grow for multiline input ${JSON.stringify({ shortShellHeight, longShellHeight })}`)
  assert(
    longComposerBox.scrollHeight > longComposerBox.clientHeight && ['auto', 'scroll'].includes(longComposerBox.overflowY),
    `Expected long composer content to cap height and scroll ${JSON.stringify(longComposerBox)}`,
  )
  await composer.fill('查退款')
  const assistantCountBeforeSend = await panel.getByTestId('chatflow-assistant-message').count()
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()
  await page.waitForFunction(
    (previousCount) => {
      const panel = document.querySelector('[data-testid="test-run-panel"]')
      return (panel?.querySelectorAll('[data-testid="chatflow-assistant-message"]').length || 0) > previousCount
    },
    assistantCountBeforeSend,
    { timeout: 10000 },
  )
  assert(await panel.getByTestId('chatflow-suggested-questions').count() === 0, 'Expected suggested questions hidden after first message')
  assert(!runResponses.includes(500), `Expected no 500 run response after composer send, got ${runResponses.join(',')}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow trial chat panel e2e')
} finally {
  await browser.close()
}
