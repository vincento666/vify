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

const auditedNodes = [
  ['llm_1', 'LLM', '大模型'],
  ['condition_1', 'CONDITION', '条件'],
  ['knowledge_1', 'KNOWLEDGE', '知识检索'],
  ['api_1', 'API_CALL', 'API 调用'],
  ['tool_1', 'TOOL_CALL', '工具调用'],
  ['workflow_1', 'EXECUTE_WORKFLOW', '工作流'],
  ['agent_1', 'AGENT_CALL', '智能体'],
  ['human_transfer_1', 'TRANSFER_TO_HUMAN', '转人工'],
  ['code_1', 'CODE', '代码'],
  ['text_1', 'TEXT_PROCESS', '文本处理'],
  ['json_1', 'JSON_PARSE', 'JSON 解析'],
  ['aggregation_1', 'VARIABLE_AGGREGATION', '变量聚合'],
  ['assign_1', 'VARIABLE_ASSIGN', '变量赋值'],
  ['intent_1', 'INTENT_RECOGNITION', '意图识别'],
  ['message_1', 'MESSAGE', '消息'],
  ['question_1', 'QUESTION', '问题'],
  ['human_input_1', 'HUMAN_INPUT', '人工输入'],
  ['info_1', 'INFORMATION_COLLECTION', '信息收集'],
]

function nodeConfig(type, label) {
  if (type === 'CONDITION') {
    return {
      outputVariable: 'route',
      conditionBranches: [{ key: 'matched', logic: 'AND', conditions: [{ left: '{{start.USER_INPUT}}', operator: 'equals', right: 'vip' }] }],
    }
  }
  if (type === 'VARIABLE_AGGREGATION') {
    return { outputVariable: 'aggregate', sources: [{ name: 'source_1', value: '{{start.USER_INPUT}}' }] }
  }
  if (type === 'VARIABLE_ASSIGN') {
    return { outputVariable: 'assigned', targetScope: 'flow', targetVariable: 'topic', source: '{{start.USER_INPUT}}' }
  }
  if (type === 'INTENT_RECOGNITION') return { outputVariable: 'intent', inputSource: '{{start.USER_INPUT}}' }
  if (type === 'MESSAGE') return { outputVariable: 'content', content: 'hello {{start.USER_INPUT}}' }
  if (type === 'QUESTION') return { outputVariable: 'answer', question: 'question {{start.USER_INPUT}}' }
  if (type === 'INFORMATION_COLLECTION') return { outputVariable: 'collected', inputSource: '{{start.USER_INPUT}}' }
  if (type === 'TEXT_PROCESS') return { outputVariable: 'text', template: '{{start.USER_INPUT}}' }
  if (type === 'JSON_PARSE') return { outputVariable: 'parsed', source: '{{start.USER_INPUT}}' }
  if (type === 'CODE') return { outputVariable: 'result', code: "result = {'output': inputs.get('USER_INPUT', '')}" }
  if (type === 'API_CALL') return { outputVariable: 'apiResult', endpoint: 'https://example.test', method: 'GET' }
  if (type === 'TOOL_CALL') return { outputVariable: 'toolResult', toolName: 'lookup_order' }
  if (type === 'EXECUTE_WORKFLOW') return { outputVariable: 'child' }
  if (type === 'AGENT_CALL') return { outputVariable: 'agentAnswer', messageTemplate: '{{start.USER_INPUT}}' }
  if (type === 'TRANSFER_TO_HUMAN') return { outputVariable: 'handoff', message: 'handoff {{start.USER_INPUT}}' }
  if (type === 'HUMAN_INPUT') return { outputVariable: 'human', prompt: 'review {{start.USER_INPUT}}' }
  return { outputVariable: label.toLowerCase().replace(/\s+/g, '_') }
}

async function ensureInputSectionOpen(section) {
  if (await section.getByRole('button', { name: '添加输入变量', exact: true }).count() > 0) return
  const toggle = section.locator('.config-section-toggle')
  if (await toggle.count() === 1) await toggle.click()
}

async function assertOfficialStartPicker(picker, sourceTestId, optionTestId, nodeLabel) {
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  const sourceList = picker.locator(`[data-testid="${sourceTestId.replace('-item', '-list')}"]`)
  const sourceText = await sourceList.innerText()
  assert(sourceText.includes('开始'), `${nodeLabel} picker should show connected START source, got ${sourceText}`)
  for (const staleSource of ['用户变量', '应用变量', '系统变量', '会话变量', '用户画像']) {
    assert(!sourceText.includes(staleSource), `${nodeLabel} picker should hide stale source ${staleSource}, got ${sourceText}`)
  }
  assert(await picker.locator('.variable-picker-columns').count() === 0, `${nodeLabel} picker must not render old two-column selector`)
  assert(await picker.locator('[data-testid="variable-source-arrow"]').count() >= 1, `${nodeLabel} picker should mark expandable source rows`)
  assert(await picker.locator('.variable-source-icon, .coze-variable-source-item svg, .coze-variable-source-item small, .coze-variable-source-item em').count() === 0, `${nodeLabel} picker must stay minimal`)
  await picker.locator(`[data-testid="${sourceTestId}"]`, { hasText: '开始' }).click()
  const itemText = await picker.locator(`[data-testid="${optionTestId.replace('-option', '-item-list')}"]`).innerText()
  assert(itemText.includes('USER_INPUT'), `${nodeLabel} picker should expose START USER_INPUT, got ${itemText}`)
  assert(itemText.includes('String'), `${nodeLabel} picker should use full type names, got ${itemText}`)
  assert(!itemText.includes('str.'), `${nodeLabel} picker should not use compact type names, got ${itemText}`)
  assert(!itemText.includes('start.USER_INPUT'), `${nodeLabel} picker should not prefix variable names, got ${itemText}`)
  assert(!itemText.includes('sys.query'), `${nodeLabel} picker should not expose legacy sys.query by default, got ${itemText}`)
  await picker.locator(`[data-testid="${optionTestId}"]`, { hasText: 'USER_INPUT' }).click()
}

async function assertAggregationStartPicker(panel) {
  const groupSection = panel.getByTestId('config-section-变量分组')
  await groupSection.waitFor({ state: 'visible', timeout: 5000 })
  const rows = groupSection.getByTestId('aggregation-group-variable-row')
  const rowCount = await rows.count()
  assert(rowCount > 0, 'Variable aggregation must expose grouped variable rows')
  const row = rows.nth(rowCount - 1)
  await row.getByRole('button', { name: '选择聚合变量', exact: true }).click()
  const picker = row.getByTestId('structured-variable-picker')
  await assertOfficialStartPicker(picker, 'structured-variable-source-item', 'structured-variable-option', '变量聚合')
  const chipText = await row.getByTestId('aggregation-variable-chip').innerText()
  assert(chipText.includes('USER_INPUT'), `Variable aggregation chip should show USER_INPUT, got ${chipText}`)
}

async function assertAssignmentStartPicker(panel) {
  const inputSection = panel.getByTestId('config-section-输入')
  await inputSection.waitFor({ state: 'visible', timeout: 5000 })
  const editor = inputSection.getByTestId('variable-assignment-editor')
  await editor.waitFor({ state: 'visible', timeout: 5000 })
  assert(
    await editor.getByLabel('赋值来源类型', { exact: true }).count() === 0,
    'Variable assignment must not expose the old source type selector',
  )
  if ((await editor.getByRole('button', { name: '清除赋值内容变量引用', exact: true }).count()) > 0) {
    await editor.getByRole('button', { name: '清除赋值内容变量引用', exact: true }).click()
  }
  await editor.getByRole('button', { name: '选择赋值内容变量', exact: true }).click()
  const picker = editor.getByTestId('structured-variable-picker')
  await assertOfficialStartPicker(picker, 'structured-variable-source-item', 'structured-variable-option', '变量赋值')
  const chipText = await editor.getByTestId('assignment-variable-chip').innerText()
  assert(chipText.includes('USER_INPUT'), `Variable assignment chip should show USER_INPUT, got ${chipText}`)
}

async function closeConfigPanelIfOpen(page) {
  const panel = page.getByTestId('node-config-panel')
  if ((await panel.count()) === 0) return
  if (!(await panel.isVisible().catch(() => false))) return
  const closeButton = panel.getByRole('button', { name: '关闭配置', exact: true })
  if ((await closeButton.count()) > 0) {
    await closeButton.click()
    await panel.waitFor({ state: 'detached', timeout: 5000 }).catch(async () => {
      await panel.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
    })
  }
}

async function selectedPanelTitle(page) {
  const panel = page.getByTestId('node-config-panel')
  if ((await panel.count()) === 0) return ''
  return panel.locator('.config-header h3').innerText().catch(() => '')
}

async function selectCanvasNode(page, nodeKey, expectedTitle) {
  await closeConfigPanelIfOpen(page)
  const node = page.locator(`.vue-flow__node[data-id="${nodeKey}"]`)
  await node.waitFor({ state: 'attached', timeout: 5000 })
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      await node.click({ force: true, timeout: 5000 })
    } catch {
      await page.evaluate((key) => {
        const element = document.querySelector(`.vue-flow__node[data-id="${key}"]`)
        element?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }))
      }, nodeKey)
    }
    const panel = page.getByTestId('node-config-panel')
    await panel.waitFor({ state: 'visible', timeout: 5000 })
    const title = (await selectedPanelTitle(page)).trim()
    if (!expectedTitle || title === expectedTitle) return
    await closeConfigPanelIfOpen(page)
  }
  const title = (await selectedPanelTitle(page)).trim()
  if (title !== expectedTitle) {
    await page.evaluate((key) => {
      const element = document.querySelector(`.vue-flow__node[data-id="${key}"]`)
      element?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }))
    }, nodeKey)
  }
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const finalTitle = (await selectedPanelTitle(page)).trim()
  assert(finalTitle === expectedTitle, `Expected selected node ${nodeKey} to open ${expectedTitle} panel, got ${finalTitle}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1600, height: 980 } })

try {
  const nodes = [
    { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT', 'CONVERSATION_NAME'], ui: { position: { x: 80, y: 120 } } } },
    ...auditedNodes.map(([nodeKey, type, label], index) => ({
      nodeKey,
      type,
      name: label,
      config: { ...nodeConfig(type, label), ui: { position: { x: 300 + (index % 4) * 260, y: 80 + Math.floor(index / 4) * 130 } } },
    })),
    { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 1180, y: 720 } } } },
  ]
  const edges = auditedNodes.map(([nodeKey]) => ({ sourceNodeKey: 'start', targetNodeKey: nodeKey, condition: null }))
  edges.push({ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null })

  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `All node variable audit ${Date.now()}`,
        description: 'all node variable reference picker audit',
        nodes,
        edges,
      },
    }),
    'create all-node audit chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })

  for (const [nodeKey,, label] of auditedNodes) {
    await selectCanvasNode(page, nodeKey, label)
    const panel = page.getByTestId('node-config-panel')
    await panel.waitFor({ state: 'visible', timeout: 5000 })
    if (nodeKey === 'condition_1') {
      await panel.getByTestId('condition-branch-editor').waitFor({ state: 'visible', timeout: 5000 })
      assert(
        await panel.getByTestId('config-section-输入').count() === 0,
        'Condition nodes are selector-only and must not expose a generic input section',
      )
      continue
    }
    if (nodeKey === 'aggregation_1') {
      await assertAggregationStartPicker(panel)
      continue
    }
    if (nodeKey === 'assign_1') {
      await assertAssignmentStartPicker(panel)
      continue
    }
    const inputSection = panel.getByTestId('config-section-输入')
    if ((await inputSection.count()) === 0) {
      const sections = await panel.locator('.config-section').evaluateAll((elements) =>
        elements.map((element) => ({
          testid: element.getAttribute('data-testid'),
          title: element.querySelector('.config-section-toggle strong')?.textContent?.trim() || '',
        })),
      )
      throw new Error(`${label}(${nodeKey}) must expose an 输入 section for variable reference audit, got ${JSON.stringify(sections)}`)
    }
    await inputSection.waitFor({ state: 'visible', timeout: 5000 })
    await ensureInputSectionOpen(inputSection)
    const addInputButton = inputSection.getByRole('button', { name: '添加输入变量', exact: true })
    if ((await addInputButton.count()) === 0) {
      throw new Error(`${label}(${nodeKey}) 输入 section must expose 添加输入变量, got ${await inputSection.innerText()}`)
    }
    await addInputButton.click()
    const rows = inputSection.getByTestId('input-parameter-row')
    const row = rows.nth((await rows.count()) - 1)
    await row.getByPlaceholder('变量名').fill(`audit_${nodeKey}`)
    await row.getByRole('button', { name: '选择输入变量', exact: true }).click()
    const picker = row.getByTestId('input-variable-picker')
    await assertOfficialStartPicker(picker, 'input-variable-source-item', 'input-variable-option', label)
    const chipText = await row.getByTestId('input-variable-chip').innerText()
    assert(chipText.includes('USER_INPUT'), `${label} selected chip should show USER_INPUT, got ${chipText}`)
    assert(!chipText.includes('{{'), `${label} selected chip should not expose raw template text, got ${chipText}`)
  }

  await selectCanvasNode(page, 'end', '结束')
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const outputEditor = panel.getByTestId('output-parameter-editor')
  await outputEditor.waitFor({ state: 'visible', timeout: 5000 })
  const outputRow = outputEditor.getByTestId('output-parameter-row').first()
  await outputRow.getByRole('button', { name: '选择输出变量值', exact: true }).click()
  await assertOfficialStartPicker(outputRow.getByTestId('output-variable-picker'), 'output-variable-source-item', 'output-variable-option', '结束')
  const outputChipText = await outputRow.getByTestId('output-variable-chip').innerText()
  assert(outputChipText.includes('USER_INPUT'), `END output chip should show USER_INPUT, got ${outputChipText}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS all node variable reference picker audit chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
