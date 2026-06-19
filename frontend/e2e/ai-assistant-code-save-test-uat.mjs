import { chromium } from 'playwright'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://localhost:4174'
const outDir =
  process.env.HIFY_E2E_ARTIFACT_DIR ||
  'artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.20-code-save-test-uat'
const openRouterApiKey = process.env.HIFY_AI_ASSISTANT_OPENROUTER_API_KEY || ''
const forceDeterministic = process.env.HIFY_AI_ASSISTANT_FORCE_DETERMINISTIC === '1' || !openRouterApiKey
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const targetPath = 'tmp/ai-assistant-code-save-test-uat.mjs'
const targetAbsPath = path.join(projectRoot, targetPath)

const savedCode = `export function classifyHarnessEvent(event) {
  if (!event || typeof event.type !== 'string') return 'unknown';
  if (event.type === 'sandbox.denied') return 'blocked';
  if (event.type.startsWith('tool.')) return 'tool';
  if (event.type.startsWith('approval.')) return 'approval';
  return 'other';
}

const cases = [
  [{ type: 'tool.call_completed' }, 'tool'],
  [{ type: 'approval.granted' }, 'approval'],
  [{ type: 'sandbox.denied' }, 'blocked'],
];

for (const [input, expected] of cases) {
  const actual = classifyHarnessEvent(input);
  if (actual !== expected) {
    throw new Error(\`expected \${expected}, got \${actual}\`);
  }
}

console.log('PASS ai-assistant-code-save-test-uat');
`

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrapResponse(response, label) {
  const payload = await response.json()
  assert(response.ok(), `${label} failed with HTTP ${response.status()}: ${JSON.stringify(payload)}`)
  assert(payload.code === 200, `${label} returned non-success envelope: ${JSON.stringify(payload)}`)
  return payload.data
}

async function installDeterministicRoutes(page) {
  if (!forceDeterministic) return
  await page.route('**/api/v1/ai-assistant/sessions/*/messages/async', async (route) => {
    const request = route.request()
    const payload = JSON.parse(request.postData() || '{}')
    payload.modelMode = 'deterministic'
    delete payload.modelConfig
    delete payload.toolName
    delete payload.toolInput

    if (String(payload.message || '').includes('运行刚才保存的测试')) {
      payload.approvalMode = 'always_approve'
      payload.toolName = 'run_shell'
      payload.toolInput = { command: `node ${targetPath}` }
      delete payload.toolCalls
    } else {
      payload.approvalMode = 'ask_each_time'
      payload.toolCalls = [
        {
          toolName: 'write_workspace_file',
          toolInput: { path: targetPath, content: savedCode },
        },
        { toolName: 'read_workspace_file', toolInput: { path: targetPath } },
      ]
    }

    await route.continue({
      headers: { ...request.headers(), 'content-type': 'application/json' },
      postData: JSON.stringify(payload),
    })
  })
}

async function configureLiveModel(page) {
  if (!openRouterApiKey || forceDeterministic) return
  await page.getByTestId('ai-assistant-model-config-icon').click()
  await page.getByTestId('ai-assistant-model-base-url').fill('https://openrouter.ai/api/v1')
  await page.getByTestId('ai-assistant-model-api-key').fill(openRouterApiKey)
}

async function submitPrompt(page, text) {
  await page.getByPlaceholder('输入给 AI 助手的消息').fill(text)
  const responsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().includes('/api/v1/ai-assistant/sessions/') &&
      response.url().endsWith('/messages/async'),
    { timeout: 30000 },
  )
  await page.getByTestId('ai-assistant-send').click()
  return unwrapResponse(await responsePromise, 'AI Assistant async message')
}

async function waitForRunTerminal(page, runId) {
  const terminal = new Set(['COMPLETED', 'FAILED', 'DENIED', 'WAITING_APPROVAL'])
  let latest = null
  for (let index = 0; index < 80; index += 1) {
    const response = await page.request.get(`${baseUrl}/api/v1/ai-assistant/runs/${runId}`)
    latest = await unwrapResponse(response, `run ${runId}`)
    if (terminal.has(latest.status)) return latest
    await page.waitForTimeout(500)
  }
  throw new Error(`timed out waiting for run ${runId} terminal status; latest=${JSON.stringify(latest)}`)
}

async function expandAllRunEchoes(page) {
  await page.evaluate(() => {
    for (const header of document.querySelectorAll('[data-testid="ai-assistant-run-event-group-header"]')) {
      if (header.getAttribute('aria-expanded') === 'false') header.click()
    }
    for (const header of document.querySelectorAll('[data-testid="ai-assistant-event-card-header"]')) {
      if (header.getAttribute('aria-expanded') === 'false') header.click()
    }
  })
}

async function approveLatestWrite(page) {
  await page.getByTestId('ai-assistant-approval-approve').last().waitFor({ state: 'visible', timeout: 60000 })
  const approvalResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().includes('/api/v1/ai-assistant/approvals/') &&
      response.url().endsWith('/approve'),
    { timeout: 30000 },
  )
  await page.getByTestId('ai-assistant-approval-approve').last().click()
  assert((await approvalResponse).ok(), 'expected approval API to succeed')
}

async function collectUiState(page) {
  return page.evaluate(() => {
    const all = (selector) => Array.from(document.querySelectorAll(selector))
    const textList = (selector) => all(selector).map((node) => node.textContent?.trim() || '')
    const iconOnlyButtons = [
      'ai-assistant-delete-session',
      'ai-assistant-message-copy',
      'ai-assistant-completion-copy',
      'ai-assistant-completion-like',
      'ai-assistant-completion-dislike',
      'ai-assistant-add-context',
      'ai-assistant-model-config-icon',
      'ai-assistant-send',
    ].map((testId) => {
      const node = document.querySelector(`[data-testid="${testId}"]`)
      const rect = node?.getBoundingClientRect()
      return {
        testId,
        present: Boolean(node),
        text: node?.textContent?.trim() || '',
        svgCount: node?.querySelectorAll('svg').length || 0,
        size: rect ? `${Number(rect.width.toFixed(2))}x${Number(rect.height.toFixed(2))}` : '',
      }
    })
    return {
      runHeaders: textList('[data-testid="ai-assistant-run-event-group-header"]'),
      eventHeaders: textList('[data-testid="ai-assistant-event-card-header"]'),
      eventDetails: textList('[data-testid="ai-assistant-event-detail-panel"]'),
      userMessages: textList('[data-testid="ai-assistant-user-message"]'),
      finalAnswers: textList('[data-testid="ai-assistant-run-final-answer"]'),
      taskRows: textList('[data-testid="ai-assistant-task-row"]'),
      toolRows: textList('[data-testid="ai-assistant-tool-call-row"]'),
      recentErrors: textList('[data-testid="ai-assistant-recent-error-row"]'),
      approvalRows: textList('[data-testid="ai-assistant-approval-row"]'),
      iconOnlyButtons,
      iconButtonSizes: Array.from(new Set(iconOnlyButtons.filter((item) => item.present).map((item) => item.size))),
      chevrons: all('.ai-collapse-chevron').map((node) => ({
        text: node.textContent?.trim() || '',
        hasSvg: Boolean(node.querySelector('svg')),
        ariaHidden: node.getAttribute('aria-hidden'),
      })),
      pageOverflowY: document.documentElement.scrollHeight - window.innerHeight,
    }
  })
}

async function run() {
  fs.mkdirSync(path.join(projectRoot, outDir, 'screenshots'), { recursive: true })
  fs.rmSync(targetAbsPath, { force: true })

  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const eventsByRun = {}

  try {
    await installDeterministicRoutes(page)
    await page.goto(`${baseUrl}/ai-assistant`, { waitUntil: 'networkidle' })
    await page.getByTestId('ai-assistant-shell').waitFor({ state: 'visible', timeout: 10000 })
    await page.getByTestId('ai-assistant-new-session').click()
    await configureLiveModel(page)

    const savePrompt = [
      '请完成一次代码保存验收：',
      `编写一份可直接用 node 运行的 JS 测试代码并保存到 ${targetPath}；`,
      '代码需要包含一个 classifyHarnessEvent 函数和三个自检 case；',
      '保存后请读回这个文件确认内容已经落盘；',
      '最后用中文总结保存和读回结果。',
    ].join('')
    const saveRun = await submitPrompt(page, savePrompt)
    await page.getByTestId('ai-assistant-approval-approve').last().waitFor({ state: 'visible', timeout: 60000 })
    await page.screenshot({ path: path.join(projectRoot, outDir, 'screenshots/code-save-before-approval.png'), fullPage: true })
    await approveLatestWrite(page)
    await page.getByTestId('ai-assistant-run-final-answer').last().waitFor({ state: 'visible', timeout: 60000 })
    await expandAllRunEchoes(page)
    await page.screenshot({ path: path.join(projectRoot, outDir, 'screenshots/code-save-completed.png'), fullPage: true })

    assert(fs.existsSync(targetAbsPath), `expected ${targetPath} to exist after AI Assistant write`)
    const savedContent = fs.readFileSync(targetAbsPath, 'utf8')
    assert(savedContent.includes('classifyHarnessEvent'), 'expected saved code to contain classifyHarnessEvent')
    const localTestOutput = execFileSync('node', [targetAbsPath], { cwd: projectRoot, encoding: 'utf8' }).trim()
    fs.writeFileSync(path.join(projectRoot, outDir, 'saved-code-test-output.txt'), `${localTestOutput}\n`)
    assert(localTestOutput.includes('PASS ai-assistant-code-save-test-uat'), `unexpected saved test output: ${localTestOutput}`)

    const shellPrompt = [
      `请运行刚才保存的测试：node ${targetPath}。`,
      '如果当前 harness 沙箱阻断 shell，请把阻断结果作为可回溯事件显示。',
    ].join('')
    const shellRun = await submitPrompt(page, shellPrompt)
    const terminalShellRun = await waitForRunTerminal(page, shellRun.runId)
    await page.reload({ waitUntil: 'networkidle' })
    await page.getByTestId('ai-assistant-shell').waitFor({ state: 'visible', timeout: 10000 })
    await page.getByTestId('ai-assistant-run-event-group-header').first().waitFor({ state: 'visible', timeout: 30000 })
    await expandAllRunEchoes(page)
    await page.screenshot({ path: path.join(projectRoot, outDir, 'screenshots/code-save-test-completed.png'), fullPage: true })

    for (const run of [saveRun, shellRun]) {
      const response = await page.request.get(`${baseUrl}/api/v1/ai-assistant/runs/${run.runId}/events`)
      eventsByRun[run.runId] = (await unwrapResponse(response, `run ${run.runId} events`)).list
    }

    const state = await collectUiState(page)
    const saveEventTypes = eventsByRun[saveRun.runId].map((event) => event.type)
    const shellEventTypes = eventsByRun[shellRun.runId].map((event) => event.type)
    const summary = {
      mode: forceDeterministic ? 'deterministic-tool-stress' : 'live-qwen',
      saveRunId: saveRun.runId,
      shellRunId: shellRun.runId,
      shellStatus: terminalShellRun.status,
      savedFile: targetPath,
      savedBytes: savedContent.length,
      localTestOutput,
      saveEventTypes,
      shellEventTypes,
      ui: state,
    }
    fs.writeFileSync(path.join(projectRoot, outDir, 'code-save-test-uat.json'), JSON.stringify(summary, null, 2))

    assert(saveEventTypes.includes('approval.required'), 'expected write approval event')
    assert(saveEventTypes.includes('approval.granted'), 'expected approval granted event')
    assert(saveEventTypes.includes('tool.call_output'), 'expected write/read tool output events')
    assert(shellEventTypes.includes('sandbox.denied'), 'expected run_shell to be blocked by sandbox.denied')
    assert(
      terminalShellRun.status === 'DENIED' || terminalShellRun.result?.sandboxDenied,
      `expected shell run denied, got ${terminalShellRun.status}`,
    )
    assert(state.runHeaders.length >= 1, `expected at least one persisted run record, got ${state.runHeaders.length}`)
    assert(state.eventHeaders.some((text) => text.includes('已编辑')), `expected file edit echo, got ${state.eventHeaders.join(' | ')}`)
    assert(state.eventHeaders.some((text) => text.includes('已读取')), `expected file read echo, got ${state.eventHeaders.join(' | ')}`)
    assert(
      state.eventHeaders.some((text) => text.includes('沙箱')) ||
        state.eventDetails.some((text) => text.includes('sandbox') || text.includes('shell-like')) ||
        state.recentErrors.some((text) => text.includes('沙箱') || text.includes('shell-like')),
      `expected visible sandbox denial echo, got headers=${state.eventHeaders.join(' | ')}, errors=${state.recentErrors.join(' | ')}`,
    )
    assert(state.finalAnswers.length >= 1, 'expected final answer for saved-code run')
    assert(state.iconButtonSizes.length === 1, `expected unified icon button size, got ${state.iconButtonSizes.join(', ')}`)
    assert(
      state.chevrons.length === 0 || state.chevrons.every((item) => item.hasSvg && item.text === '' && item.ariaHidden === 'true'),
      `expected svg-only chevrons, got ${JSON.stringify(state.chevrons)}`,
    )
    assert(state.pageOverflowY <= 2, `expected one-screen shell, got vertical overflow ${state.pageOverflowY}`)

    console.log(JSON.stringify(summary, null, 2))
  } finally {
    await browser.close()
  }
}

await run()
