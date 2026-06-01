import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const workflowScreenshotPath = process.env.HIFY_E2E_WORKFLOW_SCREENSHOT
const chatflowScreenshotPath = process.env.HIFY_E2E_CHATFLOW_SCREENSHOT
const startPopoverScreenshotPath = process.env.HIFY_E2E_START_POPOVER_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function createFlow(page, path, data) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/${path}`, { data }),
    `create ${path}`,
  )
}

async function getFlow(page, path, id) {
  return unwrap(
    await page.request.get(`${baseUrl}/api/v1/${path}/${id}`),
    `get ${path}`,
  )
}

async function runWorkflowUx(page, marker) {
  const startVariables = [
    'route',
    'intent',
    'locale',
    'channel',
    'sys.conversation_id',
  ]
  const workflow = await createFlow(page, 'workflows', {
    name: `Workflow Canvas UX ${marker}`,
    description: 'browser e2e',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: { outputVariables: startVariables, ui: { position: { x: 500, y: 180 } } },
      },
      {
        nodeKey: 'condition_1',
        type: 'CONDITION',
        name: '条件',
        config: { expression: '{{start.USER_INPUT}}', outputVariable: 'route', ui: { position: { x: 200, y: 420 } } },
      },
      {
        nodeKey: 'llm_1',
        type: 'LLM',
        name: '大模型',
        config: { prompt: `Return ${marker}`, outputVariable: 'answer', ui: { position: { x: 180, y: 160 } } },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: { outputVariable: 'answer', output: '{{llm_1.answer}}', ui: { position: { x: 90, y: 320 } } },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'condition_1', condition: null },
      { sourceNodeKey: 'condition_1', targetNodeKey: 'llm_1', condition: 'run' },
      { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
    ],
  })

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  assert(await page.getByRole('button', { name: '开放', exact: true }).count() === 1, 'Expected 开放 lifecycle tab')
  assert(await page.getByRole('button', { name: 'Open API', exact: true }).count() === 0, 'Expected topbar Open API duplicate to be removed')
  assert(await page.getByRole('button', { name: '快速连线', exact: true }).count() === 0, 'Expected 快速连线 action to be removed')

  const startNode = page.locator('.vue-flow__node[data-id="start"]')
  const variableList = startNode.locator('[data-testid="start-variable-list"]')
  await variableList.waitFor({ state: 'visible', timeout: 5000 })
  const variableTitle = await variableList.getAttribute('title')
  assert(variableTitle === null, 'Expected START variable list to avoid the native title tooltip when using the custom summary popover')
  await variableList.hover()
  await page.waitForTimeout(300)
  assert(
    await page.locator('.el-popper', { hasText: 'str.sys.conversation_id' }).count() === 0,
    'Expected START variable hover to use only the native title tooltip, not an Element Plus tooltip',
  )
  const variablePopover = startNode.locator('[data-testid="start-variable-popover"]')
  await variablePopover.waitFor({ state: 'visible', timeout: 5000 })
  const popoverState = await variablePopover.evaluate((element) => {
    const style = window.getComputedStyle(element)
    const rect = element.getBoundingClientRect()
    const tagElements = Array.from(element.querySelectorAll('.node-variable-popover-badge'))
    const tags = tagElements.map((tag) => tag.textContent?.trim() || '')
    const clippedTags = tagElements
      .filter((tag) => tag.scrollWidth > tag.clientWidth + 1)
      .map((tag) => tag.textContent?.trim() || '')
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    const topElement = document.elementFromPoint(centerX, centerY)
    return {
      backgroundColor: style.backgroundColor,
      display: style.display,
      flexWrap: style.flexWrap,
      visibility: style.visibility,
      width: rect.width,
      isTopLayer: Boolean(topElement && element.contains(topElement)),
      clippedTags,
      tags,
    }
  })
  assert(popoverState.visibility === 'visible', `Expected START variable popover to be visible, got ${JSON.stringify(popoverState)}`)
  assert(popoverState.backgroundColor === 'rgb(255, 255, 255)', `Expected START variable popover to use a white surface, got ${popoverState.backgroundColor}`)
  assert(popoverState.flexWrap === 'wrap', `Expected START variable popover badges to wrap, got ${popoverState.flexWrap}`)
  assert(popoverState.width > 220 && popoverState.width < 520, `Expected START variable popover to fit content, got ${popoverState.width}`)
  assert(popoverState.isTopLayer, `Expected START variable popover to render above neighboring nodes, got ${JSON.stringify(popoverState)}`)
  assert(popoverState.clippedTags.length === 0, `Expected START variable popover to show full variable names, clipped ${popoverState.clippedTags.join(', ')}`)
  for (const value of startVariables) {
    assert(popoverState.tags.includes(`str.${value}`), `Expected START variable popover to include str.${value}, got ${popoverState.tags.join(', ')}`)
  }
  if (startPopoverScreenshotPath) await page.screenshot({ path: startPopoverScreenshotPath, fullPage: true })
  const startBox = await startNode.boundingBox()
  assert(startBox && startBox.height <= 150, `Expected START node to keep a fixed height, got ${startBox?.height}`)
  const variableOverflow = await variableList.evaluate((element, allVariables) => {
    const style = window.getComputedStyle(element)
    const node = element.closest('.coze-node')
    const sourcePort = node?.querySelector('.source-port')
    const nodeStyle = node ? window.getComputedStyle(node) : null
    const rect = element.getBoundingClientRect()
    const badges = Array.from(element.querySelectorAll('.node-variable-badge'))
    const more = element.querySelector('[data-testid="start-variable-more"]')
    const gap = Number.parseFloat(style.columnGap || style.gap || '0') || 0
    const nextValue = allVariables[badges.length]
    let nextWidth = 0
    if (nextValue) {
      const probe = document.createElement('em')
      probe.className = 'node-variable-badge'
      probe.textContent = `str.${nextValue}`
      probe.style.position = 'absolute'
      probe.style.visibility = 'hidden'
      element.appendChild(probe)
      nextWidth = probe.getBoundingClientRect().width
      probe.remove()
    }
    const occupiedWidth = badges.reduce((total, badge, index) => (
      total + badge.getBoundingClientRect().width + (index > 0 ? gap : 0)
    ), 0) + (more ? gap + more.getBoundingClientRect().width : 0)
    return {
      overflowX: style.overflowX,
      listWidth: rect.width,
      visibleBadgeCount: badges.length,
      moreText: element.querySelector('[data-testid="start-variable-more"]')?.textContent?.trim() || '',
      nodeOverflow: nodeStyle?.overflow || '',
      hasSourcePort: Boolean(sourcePort),
      occupiedWidth,
      nextWidth,
      wouldOverflowWithNext: nextWidth > 0 && occupiedWidth + gap + nextWidth > rect.width,
    }
  }, startVariables)
  assert(variableOverflow.overflowX === 'hidden', `Expected START variables to be clipped, got ${variableOverflow.overflowX}`)
  assert(variableOverflow.visibleBadgeCount === 3, `Expected START to show variables until the next one would exceed width, got ${variableOverflow.visibleBadgeCount}`)
  assert(variableOverflow.visibleBadgeCount < startVariables.length, 'Expected START to show a fixed number of variables only')
  assert(variableOverflow.moreText === '...', `Expected overflowed START variables to collapse into a trailing ..., got ${variableOverflow.moreText}`)
  assert(variableOverflow.wouldOverflowWithNext, `Expected next START variable to overflow before collapsing, got ${JSON.stringify(variableOverflow)}`)
  assert(variableOverflow.hasSourcePort, 'Expected START node to keep the right-side source endpoint')
  assert(variableOverflow.nodeOverflow === 'visible', `Expected START node overflow to keep endpoint visible, got ${variableOverflow.nodeOverflow}`)

  await page.getByLabel('折叠侧栏').click()
  assert(await page.locator('[data-testid="canvas-resource-panel"]').count() === 0, 'Expected canvas side panel to collapse')
  await page.getByLabel('展开侧栏').click()
  await page.locator('[data-testid="canvas-resource-panel"]').waitFor({ state: 'visible', timeout: 5000 })

  await page.getByRole('button', { name: '自动布局' }).click()
  const saveResponse = page.waitForResponse((response) =>
    response.url().includes(`/api/v1/workflows/${workflow.id}`)
      && response.request().method() === 'PUT',
  )
  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await saveResponse
  const saved = await getFlow(page, 'workflows', workflow.id)
  const byKey = new Map(saved.nodes.map((node) => [node.nodeKey, node]))
  assert(byKey.get('start').config.ui.position.x < byKey.get('condition_1').config.ui.position.x, 'Expected START to be left of CONDITION after auto layout')
  assert(byKey.get('condition_1').config.ui.position.x < byKey.get('llm_1').config.ui.position.x, 'Expected CONDITION to be left of LLM after auto layout')
  assert(byKey.get('llm_1').config.ui.position.x < byKey.get('end').config.ui.position.x, 'Expected LLM to be left of END after auto layout')
  assert(
    saved.edges.some((edge) => edge.sourceNodeKey === 'condition_1' && edge.targetNodeKey === 'llm_1' && edge.condition === 'run'),
    'Expected conditional edge to survive auto layout and save',
  )

  if (workflowScreenshotPath) await page.screenshot({ path: workflowScreenshotPath, fullPage: true })
}

async function runWorkflowMultiConditionUat(page, marker) {
  const llmExpected = `WORKFLOW_COMPLEX_${marker}`
  const workflow = await createFlow(page, 'workflows', {
    name: `Workflow Multi Condition UAT ${marker}`,
    description: 'multi condition browser e2e',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 96 } } },
      },
      {
        nodeKey: 'router',
        type: 'CONDITION',
        name: '条件',
        config: { expression: '{{start.USER_INPUT}}', outputVariable: 'route', ui: { position: { x: 640, y: 96 } } },
      },
      {
        nodeKey: 'refund_llm',
        type: 'LLM',
        name: '退款 LLM 分支',
        config: {
          prompt: `Return exactly this token and nothing else: ${llmExpected}`,
          outputVariable: 'answer',
          ui: { position: { x: 1160, y: 0 } },
        },
      },
      {
        nodeKey: 'invoice',
        type: 'API_CALL',
        name: '发票分支',
        config: { method: 'GET', url: `INVOICE_BRANCH_${marker}`, outputVariable: 'answer', ui: { position: { x: 1160, y: 180 } } },
      },
      {
        nodeKey: 'fallback',
        type: 'API_CALL',
        name: '默认分支',
        config: { method: 'GET', url: `DEFAULT_BRANCH_${marker}`, outputVariable: 'answer', ui: { position: { x: 1160, y: 360 } } },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: {
          outputVariable: 'answer',
          output: '{{refund_llm.answer}}{{invoice.answer}}{{fallback.answer}}',
          ui: { position: { x: 1680, y: 180 } },
        },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'router', condition: null },
      { sourceNodeKey: 'router', targetNodeKey: 'refund_llm', condition: 'refund' },
      { sourceNodeKey: 'router', targetNodeKey: 'invoice', condition: 'invoice' },
      { sourceNodeKey: 'router', targetNodeKey: 'fallback', condition: null },
      { sourceNodeKey: 'refund_llm', targetNodeKey: 'end', condition: null },
      { sourceNodeKey: 'invoice', targetNodeKey: 'end', condition: null },
      { sourceNodeKey: 'fallback', targetNodeKey: 'end', condition: null },
    ],
  })

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '试运行' }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert((await panel.innerText()).includes('用户消息（userMessage / USER_INPUT）'), 'Expected workflow run input to name userMessage and USER_INPUT')

  for (const [input, expected] of [
    ['refund', llmExpected],
    ['invoice', `INVOICE_BRANCH_${marker}`],
    ['other', `DEFAULT_BRANCH_${marker}`],
  ]) {
    await panel.getByPlaceholder('输入 userMessage').fill(input)
    await panel.getByRole('button', { name: '运行', exact: true }).click()
    const output = panel.locator('[data-testid="workflow-run-output"]')
    await output.waitFor({ state: 'visible', timeout: 60000 })
    let outputText = await output.innerText()
    for (let attempt = 0; attempt < 80 && !outputText.includes(expected); attempt += 1) {
      await page.waitForTimeout(750)
      outputText = await output.innerText()
    }
    assert(outputText.includes(expected), `Expected ${input} to route to ${expected}, got: ${outputText}`)
    if (input === 'refund') {
      assert(!outputText.includes('LLM mock:'), `Expected workflow refund branch to use live LLM output, got: ${outputText}`)
    }
  }
}

async function runChatflowUx(page, marker) {
  const openingText = `开场白_${marker}`
  const guideQuestion = `llm_${marker}`
  const fallbackQuestion = `fallback_${marker}`
  const answerToken = `CHATFLOW_COMPLEX_${marker}`
  const chatflow = await createFlow(page, 'chatflows', {
    name: `Chatflow Runtime UX ${marker}`,
    description: 'browser e2e',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: {
          outputVariables: ['sys.query', 'sys.conversation_id', 'sys.user_id', 'sys.channel', 'sys.round'],
          openingText,
          guideQuestions: [guideQuestion, fallbackQuestion],
          ui: { position: { x: 120, y: 96 } },
        },
      },
      {
        nodeKey: 'router',
        type: 'CONDITION',
        name: '条件',
        config: {
          expression: '{{start.sys.query}}',
          outputVariable: 'route',
          ui: { position: { x: 480, y: 96 } },
        },
      },
      {
        nodeKey: 'llm_1',
        type: 'LLM',
        name: '大模型',
        config: {
          prompt: `Return exactly this token and nothing else: ${answerToken}`,
          outputVariable: 'answer',
          ui: { position: { x: 840, y: 24 } },
        },
      },
      {
        nodeKey: 'fallback',
        type: 'API_CALL',
        name: '默认回复',
        config: {
          method: 'GET',
          url: `CHATFLOW_FALLBACK_${marker}`,
          outputVariable: 'answer',
          ui: { position: { x: 840, y: 240 } },
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: { outputVariable: 'output', output: '{{llm_1.answer}}{{fallback.answer}}', ui: { position: { x: 1200, y: 120 } } },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'router', condition: null },
      { sourceNodeKey: 'router', targetNodeKey: 'llm_1', condition: guideQuestion },
      { sourceNodeKey: 'router', targetNodeKey: 'fallback', condition: null },
      { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
      { sourceNodeKey: 'fallback', targetNodeKey: 'end', condition: null },
    ],
  })

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  for (const nodeKey of ['start', 'router', 'llm_1', 'fallback', 'end']) {
    await page.locator(`.vue-flow__node[data-id="${nodeKey}"]`).waitFor({ state: 'visible', timeout: 5000 })
  }
  await page.getByRole('button', { name: '对话试运行' }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const inputPanelText = await panel.innerText()
  for (const label of ['用户消息（sys.query）', '会话 ID（sys.conversation_id）', '用户 ID（sys.user_id）', '渠道（sys.channel）']) {
    assert(inputPanelText.includes(label), `Expected chatflow run input label ${label}`)
  }
  await panel.getByTestId('chatflow-opening-message').waitFor({ state: 'visible', timeout: 5000 })
  assert((await panel.getByTestId('chatflow-opening-message').innerText()).includes(openingText), 'Expected opening text to appear before a user run')
  const suggested = panel.getByTestId('chatflow-suggested-questions')
  await suggested.waitFor({ state: 'visible', timeout: 5000 })
  assert((await suggested.innerText()).includes('猜你想问'), 'Expected guide questions to appear as separate 猜你想问 choices')
  assert(!(await suggested.innerText()).includes(openingText), 'Expected guide questions to stay separate from the opening text')
  const guideLayout = await suggested.locator('.chatflow-guide-list').evaluate((element) => ({
    direction: window.getComputedStyle(element).flexDirection,
    alignItems: window.getComputedStyle(element).alignItems,
    listWidth: element.getBoundingClientRect().width,
    buttonWidth: element.querySelector('button')?.getBoundingClientRect().width || 0,
    buttonTextAlign: element.querySelector('button') ? window.getComputedStyle(element.querySelector('button')).textAlign : '',
  }))
  assert(guideLayout.direction === 'column', `Expected suggested questions to be vertical, got ${guideLayout.direction}`)
  assert(guideLayout.alignItems === 'flex-start', `Expected suggested question bubbles to be left aligned, got ${guideLayout.alignItems}`)
  assert(guideLayout.buttonTextAlign === 'left', `Expected suggested question text to be left aligned, got ${guideLayout.buttonTextAlign}`)
  assert(guideLayout.buttonWidth < guideLayout.listWidth * 0.8, `Expected suggested question bubble width to fit content, got ${JSON.stringify(guideLayout)}`)

  await panel.getByRole('button', { name: guideQuestion, exact: true }).click()
  assert(await panel.getByPlaceholder('输入用户消息').inputValue() === guideQuestion, 'Expected guide question to fill the chat input')
  assert(await suggested.isVisible(), 'Expected guide question choices to remain visible after the user picks one')
  assert((await suggested.innerText()).includes(guideQuestion), 'Expected selected guide question to remain available after click')

  await panel.getByRole('button', { name: '运行', exact: true }).click()
  const assistant = panel.getByTestId('chatflow-assistant-message')
  await assistant.waitFor({ state: 'visible', timeout: 10000 })
  const panelText = await panel.innerText()
  assert(panelText.includes('SUCCEEDED'), 'Expected chatflow run to succeed')
  assert(panelText.includes(openingText), 'Expected opening text to remain in the conversation result')
  assert(panelText.includes('猜你想问'), 'Expected suggested questions to remain visually distinct in the conversation result')
  const assistantText = await assistant.innerText()
  assert(assistantText.includes(answerToken), `Expected chatflow complex LLM branch to return ${answerToken}, got ${assistantText}`)
  assert(!assistantText.includes('LLM mock:'), `Expected chatflow complex branch to use live LLM output, got ${assistantText}`)
  assert(await panel.locator('.run-result').count() === 0, 'Expected chatflow trial panel to avoid raw JSON code block')

  if (chatflowScreenshotPath) await page.screenshot({ path: chatflowScreenshotPath, fullPage: true })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const marker = `UX_${Date.now()}`
  await runWorkflowUx(page, marker)
  await runWorkflowMultiConditionUat(page, marker)
  await runChatflowUx(page, marker)
  console.log('PASS workflow/chatflow canvas UX lifecycle e2e')
} finally {
  await browser.close()
}
