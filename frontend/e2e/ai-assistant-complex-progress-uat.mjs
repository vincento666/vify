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
      const status = row.querySelector('.ai-task__dot')
      const style = status ? getComputedStyle(status) : null
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
      spinner: Boolean(row.querySelector('.ai-event__spinner')),
    }))
    return {
      label: sampleLabel,
      at: Date.now(),
      runHeaders: all('[data-testid="ai-assistant-run-event-group-header"]').map((node) => node.textContent?.trim() || ''),
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
    payload.toolName = 'write_workspace_file'
    payload.toolInput = {
      path: 'tmp/ai-assistant-uat-progress.md',
      content: 'AI 助手复杂任务进度 UAT',
    }
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
      '必须调用 search_knowledge_base 检索“退票规则 和 AI 助手 harness”；',
      '必须调用 invoke_skill 记录 tdd 技能调用意图；',
      '最后必须调用 write_workspace_file 写入 tmp/ai-assistant-uat-progress.md，内容为中文三段式总结。',
      '写入前需要审批。请在工具之间输出简短中文进度，并最后给出中文总结。',
    ].join('')
    await page.getByPlaceholder('输入给 AI 助手的消息').fill(prompt)
    await page.getByTestId('ai-assistant-send').click()
    await page.getByTestId('ai-assistant-run-event-group-header').last().waitFor({ state: 'visible', timeout: 15000 })

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

    const latestHeader = page.getByTestId('ai-assistant-run-event-group-header').last()
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
      if (sample.finalAnswers.length > 0 && sample.runHeaders.some((text) => text.includes('已处理'))) break
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
      pageOverflowY: final.pageOverflowY,
    }
    fs.writeFileSync(`${outDir}/complex-progress-uat.json`, JSON.stringify({ summary, samples }, null, 2))
    console.log(JSON.stringify(summary, null, 2))
    assert(summary.sawTaskRows, 'expected task rows in the right progress panel')
    assert(summary.sawRunningTask, 'expected a running task state during execution')
    assert(summary.sawAnimatedRunningTask, 'expected running task state to animate')
    assert(summary.sawStepSpinner, 'expected running execution step spinner')
    assert(summary.finalAnswers > 0, 'expected final assistant answer')
    assert(summary.pageOverflowY <= 2, `expected one-screen shell, got overflow ${summary.pageOverflowY}`)
  } finally {
    await browser.close()
  }
}

await main()
