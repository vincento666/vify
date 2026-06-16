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
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `021.3 Chatflow Run Debug ${stamp}`,
      description: 'chatflow embedded run debug deeplink e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 140, y: 180 } } } },
        { nodeKey: 'question_1', type: 'QUESTION', name: '问题', config: { question: '继续吗？', outputVariable: 'answer', ui: { position: { x: 520, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'answer={{question_1.answer}}', ui: { position: { x: 900, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'question_1', condition: null },
        { sourceNodeKey: 'question_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create chatflow')

  const interrupted = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
    data: {
      input: {
        'sys.query': 'start warranty flow',
        'sys.conversation_id': `conv-0213-${stamp}`,
        'sys.user_id': `user-0213-${stamp}`,
        'sys.channel': 'web',
      },
    },
  }), 'run chatflow')
  const eventId = interrupted.events.at(-1).id
  const resumed = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs/${interrupted.runId}/resume`, {
    data: { eventId, resumeData: { answer: 'yes' } },
  }), 'resume chatflow')
  assert(resumed.status === 'SUCCEEDED', `Expected resumed status SUCCEEDED, got ${resumed.status}`)

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas?runId=${interrupted.runId}&debug=1`, { waitUntil: 'networkidle' })
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.waitFor({ state: 'visible', timeout: 10000 })
  const dockText = await dock.innerText()
  assert(page.url().includes(`/chatflows/${chatflow.id}/canvas`), `Expected chatflow canvas URL, got ${page.url()}`)
  assert(!page.url().includes('/observe'), `Expected no observe navigation, got ${page.url()}`)
  assert(dockText.includes(`Run #${interrupted.runId}`), `Expected run id in dock, got ${dockText}`)
  assert(dockText.includes(`conv-0213-${stamp}`), 'Expected conversation identity in dock')
  assert(!dockText.includes('事件时间线'), 'Expected event timeline to stay folded by default')
  assert(dockText.includes('调用树'), 'Expected call tree section in dock')
  assert(dockText.includes('火焰图'), 'Expected flamegraph section in dock')
  assert(dockText.includes('question_1'), 'Expected question node in dock')

  const succeededQuestionNode = dock
    .getByTestId('chatflow-run-call-tree')
    .locator('button.workflow-call-tree-node')
    .filter({ hasText: 'question_1QUESTION 成功' })
  assert(await succeededQuestionNode.count() === 1, 'Expected one succeeded question node in call tree')
  await succeededQuestionNode.click()
  const selectedText = await dock.innerText()
  assert(selectedText.includes('输出') && selectedText.includes('yes'), 'Expected resumed answer value in selected node detail')

  const advanced = dock.getByTestId('chatflow-debug-advanced')
  await advanced.locator('summary').click()
  const advancedText = await advanced.innerText()
  assert(advancedText.includes('事件时间线'), 'Expected advanced context to expose event timeline')
  assert(advancedText.includes('消息'), 'Expected message event in advanced timeline')
  assert(advancedText.includes('等待输入'), 'Expected interrupt event in advanced timeline')
  assert(advancedText.includes('继续执行'), 'Expected resume event in advanced timeline')
  assert(advancedText.includes('完成'), 'Expected done event in advanced timeline')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS chatflow run debug deeplink chatflow=${chatflow.id} run=${interrupted.runId}`)
} finally {
  await browser.close()
}
