import { chromium } from 'playwright'
import fs from 'node:fs'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const outDir =
  process.env.HIFY_E2E_ARTIFACT_DIR ||
  'artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.11-inapp-progress-uat'
const openRouterApiKey = process.env.HIFY_AI_ASSISTANT_OPENROUTER_API_KEY || ''

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function collectMetrics(page, label) {
  return page.evaluate((sampleLabel) => {
    const all = (selector) => Array.from(document.querySelectorAll(selector))
    const box = (selector) => {
      const node = document.querySelector(selector)
      if (!node) return null
      const rect = node.getBoundingClientRect()
      return { top: rect.top, bottom: rect.bottom, height: rect.height }
    }
    const taskRows = all('[data-testid="ai-assistant-task-row"]').map((row) => {
      const status = row.querySelector('[data-testid="ai-assistant-task-status-icon"]')
      const spinner = row.querySelector('[data-testid="ai-assistant-task-spinner"]')
      const style = spinner ? getComputedStyle(spinner) : null
      return {
        text: row.textContent?.trim() || '',
        statusClass: status?.className || '',
        animationName: style?.animationName || '',
        animationDuration: style?.animationDuration || '',
      }
    })
    const steps = all('[data-testid="ai-assistant-execution-step"]').map((row) => ({
      text: row.textContent?.trim() || '',
      statusClass: row.querySelector('.ai-execution-step__status')?.className || '',
      spinner: Boolean(row.querySelector('[data-testid="ai-assistant-execution-step-spinner"]')),
      done: Boolean(row.querySelector('[data-testid="ai-assistant-execution-step-done"]')),
    }))
    const eventHeaders = all('[data-testid="ai-assistant-event-card-header"]').map((node) => node.textContent?.trim() || '')
    const groupHeaders = all('[data-testid="ai-assistant-activity-toggle"]')
    const parentIcon = groupHeaders.at(-1)?.closest('[data-testid="ai-assistant-activity-row"]')
      ?.querySelector('.ai-activity-row__status')
    const parentIconRect = parentIcon?.getBoundingClientRect()
    const childIconRects = all('[data-testid="ai-assistant-event-status-icon"]').map((node) => node.getBoundingClientRect())
    const parentCenterX = parentIconRect ? parentIconRect.left + parentIconRect.width / 2 : null
    const childCenterXs = childIconRects.map((rect) => rect.left + rect.width / 2)
    const iconAlignmentMaxDelta =
      parentCenterX === null || childCenterXs.length === 0
        ? null
        : Math.max(...childCenterXs.map((centerX) => Math.abs(centerX - parentCenterX)))
    return {
      label: sampleLabel,
      at: Date.now(),
      runHeaders: all('[data-testid="ai-assistant-activity-toggle"]').map((node) => node.textContent?.trim() || ''),
      eventHeaders,
      hasHashSequence: eventHeaders.some((text) => /#\d+/.test(text)),
      iconAlignmentMaxDelta,
      taskRows,
      steps,
      taskRunningCount: taskRows.filter((row) => row.statusClass.includes('status-running')).length,
      taskRunningAnimatedCount: taskRows.filter(
        (row) => row.statusClass.includes('status-running') && row.animationName && row.animationName !== 'none',
      ).length,
      stepSpinnerCount: steps.filter((step) => step.spinner).length,
      nodeSpinnerCount: all('[data-testid="ai-assistant-node-spinner"]').length,
      approvalRows: all('[data-testid="ai-assistant-approval-row"]').map((node) => node.textContent?.trim() || ''),
      toolRows: all('[data-testid="ai-assistant-tool-call-row"]').map((node) => node.textContent?.trim() || ''),
      finalAnswers: all('[data-testid="ai-assistant-run-final-answer"]').map((node) => node.textContent?.trim() || ''),
      pageOverflowY: document.documentElement.scrollHeight - window.innerHeight,
      composerBox: box('[data-testid="ai-assistant-composer"]'),
      rightBox: box('[data-testid="ai-assistant-run-inspector"]'),
    }
  }, label)
}

async function configureLiveModel(page) {
  if (!openRouterApiKey) return
  await page.getByTestId('ai-assistant-model-config-icon').click()
  await page.getByTestId('ai-assistant-model-base-url').fill('https://openrouter.ai/api/v1')
  await page.getByTestId('ai-assistant-model-api-key').fill(openRouterApiKey)
}

async function installDeterministicFallbackIfNeeded(page) {
  if (openRouterApiKey) return
  await page.route('**/api/v1/ai-assistant/sessions/*/messages/async', async (route) => {
    const request = route.request()
    const payload = JSON.parse(request.postData() || '{}')
      payload.modelMode = 'deterministic'
    payload.toolCalls = [
      { toolName: 'write_workspace_file', toolInput: { path: 'tmp/ai-assistant-uat-progress.md', content: 'AI 助手复杂任务进度 UAT' } },
      { toolName: 'read_workspace_file', toolInput: { path: 'tmp/ai-assistant-uat-progress.md' } },
    ]
    delete payload.toolName
    delete payload.toolInput
    delete payload.modelConfig
    await route.continue({
      headers: { ...request.headers(), 'content-type': 'application/json' },
      postData: JSON.stringify(payload),
    })
  })
}

async function main() {
  fs.mkdirSync(`${outDir}/screenshots`, { recursive: true })
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const samples = []
  try {
    await installDeterministicFallbackIfNeeded(page)
    await page.goto(`${baseUrl}/ai-assistant`, { waitUntil: 'networkidle' })
    await page.getByTestId('ai-assistant-shell').waitFor({ state: 'visible', timeout: 10000 })
    await page.getByTestId('ai-assistant-new-session').click()
    await configureLiveModel(page)
    samples.push(await collectMetrics(page, 'ready'))

    const prompt = [
      '请执行一个复杂验收任务：',
      '必须调用 read_workspace_file 读取 specs/README.md；',
      '必须调用 search_workspace_files 在 specs 中检索“AI Assistant harness”；',
      '必须调用 invoke_skill 记录 tdd 技能调用意图；',
      '必须创建并写入 tmp/ai-assistant-uat-progress.md，内容为中文三段式总结；',
      '写入审批通过后必须再次调用 read_workspace_file 读取该文件校验内容。',
      '请不要要求我写工具名，自动识别读文件、工作区检索、skill、创建文件、写入文件、读取校验这些调用；工具之间输出简短中文进度，并最后给出中文总结。',
    ].join('')
    await page.getByPlaceholder('输入给 AI 助手的消息').fill(prompt)
    await page.getByTestId('ai-assistant-send').click()
    await page.getByTestId('ai-assistant-activity-toggle').last().waitFor({ state: 'visible', timeout: 60000 })

    for (let index = 0; index < 180; index += 1) {
      const sample = await collectMetrics(page, `running-${index}`)
      samples.push(sample)
      if (index === 2) {
        await page.screenshot({ path: `${outDir}/screenshots/progress-running-early.png`, fullPage: true })
      }
      const approveButtonCount = await page.getByTestId('ai-assistant-approval-approve').count()
      if (approveButtonCount > 0 || sample.finalAnswers.length > 0) break
      await page.waitForTimeout(500)
    }

    await page
      .waitForFunction(
        () =>
          Boolean(document.querySelector('[data-testid="ai-assistant-approval-approve"]')) ||
          Boolean(document.querySelector('[data-testid="ai-assistant-run-final-answer"]')),
        undefined,
        { timeout: 120000 },
      )
      .catch(() => undefined)

    const latestHeader = page.getByTestId('ai-assistant-activity-toggle').last()
    if ((await latestHeader.getAttribute('aria-expanded')) === 'false') await latestHeader.click()
    await page.screenshot({ path: `${outDir}/screenshots/progress-before-approval.png`, fullPage: true })
    samples.push(await collectMetrics(page, 'before-approval'))

    const approveButtonCount = await page.getByTestId('ai-assistant-approval-approve').count()
    if (approveButtonCount > 0) {
      const approvalResponse = page
        .waitForResponse(
          (response) =>
            response.request().method() === 'POST' &&
            response.url().includes('/api/v1/ai-assistant/approvals/') &&
            response.url().endsWith('/approve'),
          { timeout: 10000 },
        )
        .catch(() => null)
      await page.getByTestId('ai-assistant-approval-approve').last().click()
      const response = await approvalResponse
      assert(response?.ok(), 'expected approval click to call approve API')
    }

    for (let index = 0; index < 70; index += 1) {
      const sample = await collectMetrics(page, `post-approval-${index}`)
      samples.push(sample)
      if (sample.finalAnswers.length > 0 && sample.runHeaders.some((text) => text.includes('已完成'))) break
      await page.waitForTimeout(500)
    }

    await page.screenshot({ path: `${outDir}/screenshots/progress-completed.png`, fullPage: true })
    const final = await collectMetrics(page, 'completed')
    samples.push(final)
    const summary = {
      sampleCount: samples.length,
      sawTaskRows: samples.some((sample) => sample.taskRows.length > 0),
      sawRunningTask: samples.some((sample) => sample.taskRunningCount > 0),
      sawAnimatedRunningTask: samples.some((sample) => sample.taskRunningAnimatedCount > 0),
      sawStepSpinner: samples.some((sample) => sample.stepSpinnerCount > 0),
      finalHeader: final.runHeaders.at(-1),
      finalSteps: final.steps.length,
      finalToolRows: final.toolRows.length,
      finalAnswers: final.finalAnswers.length,
      finalEventHeaders: final.eventHeaders,
      hasHashSequence: final.hasHashSequence,
      iconAlignmentMaxDelta: final.iconAlignmentMaxDelta,
      finalStepTexts: final.steps.map((step) => step.text),
      finalToolTexts: final.toolRows,
      pageOverflowY: final.pageOverflowY,
    }
    fs.writeFileSync(`${outDir}/complex-progress-uat.json`, JSON.stringify({ summary, samples }, null, 2))
    console.log(JSON.stringify(summary, null, 2))
    assert(summary.sawTaskRows, 'expected task rows in the right progress panel')
    assert(summary.sawRunningTask, 'expected a running task state during execution')
    assert(summary.sawAnimatedRunningTask, 'expected running task state to animate')
    assert(summary.sawStepSpinner, 'expected running execution step spinner')
    assert(
      final.toolRows.some((row) => row.includes('写入工作区文件')) &&
        final.toolRows.filter((row) => row.includes('读取工作区文件')).length >= 2,
      `expected create/write/read verification tool calls, got: ${final.toolRows.join(' | ')}`,
    )
    assert(
      final.steps.every((step) => !/思考摘要|工具调用决策|模型输出|文件操作意图|技能调用意图/.test(step.text)),
      `expected execution steps to hide low-level react loop events: ${final.steps.map((step) => step.text).join(' | ')}`,
    )
    assert(
      final.steps.length <= final.toolRows.length + 2,
      `expected current-question execution steps only, got ${final.steps.length} steps for ${final.toolRows.length} tool calls`,
    )
    assert(!summary.hasHashSequence, `expected event headers without # sequence, got: ${summary.finalEventHeaders.join(' | ')}`)
    assert(
      summary.iconAlignmentMaxDelta === null || summary.iconAlignmentMaxDelta <= 1,
      `expected parent and child event icons to align horizontally, got delta ${summary.iconAlignmentMaxDelta}`,
    )
    assert(summary.finalAnswers > 0, 'expected final assistant answer')
    assert(summary.pageOverflowY <= 2, `expected one-screen shell, got overflow ${summary.pageOverflowY}`)
  } finally {
    await browser.close()
  }
}

await main()
