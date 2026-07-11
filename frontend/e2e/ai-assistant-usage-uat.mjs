import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5174'
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const outputDir = path.resolve(
  projectRoot,
  process.env.HIFY_E2E_ARTIFACT_DIR || 'artifacts/slices/190-ai-assistant-observability-benchmark/190.5',
)
const screenshotPath = path.join(outputDir, 'ai-assistant-token-cost-dashboard.png')
const detailScreenshotPath = path.join(outputDir, 'ai-assistant-token-cost-detail.png')
const evidencePath = path.join(outputDir, 'dom-evidence.json')

function envelope(data) {
  return { code: 200, message: 'OK', data }
}

async function fulfill(route, data) {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(envelope(data)),
  })
}

function isoDaysAgo(days) {
  const value = new Date()
  value.setHours(12, 0, 0, 0)
  value.setDate(value.getDate() - days)
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const totals = (totalTokens, costUsd, costState, sessionCount, unknownCostCount = 0) => ({
  totalTokens,
  costUsd,
  costState,
  unknownCostCount,
  unknownCostTokens: unknownCostCount ? 18_400 : 0,
  sessionCount,
  callCount: sessionCount * 3,
})

const summary = {
  today: totals(279_000, '0.9214000000', 'complete', 4),
  yesterday: totals(1_240_000, '3.8100000000', 'complete', 15),
  rolling30Days: totals(74_000_000, '212.5700000000', 'partial', 96, 3),
  cumulative: totals(2_000_000_000, '5830.4100000000', 'partial', 796, 7),
}
const emptySummary = {
  today: totals(0, '0.0000000000', 'complete', 0),
  yesterday: totals(0, '0.0000000000', 'complete', 0),
  rolling30Days: totals(0, '0.0000000000', 'complete', 0),
  cumulative: totals(0, '0.0000000000', 'complete', 0),
}

const daily = Array.from({ length: 150 }, (_, index) => {
  const tokens = index % 9 === 0 ? 0 : (index + 3) * 4100
  const unknown = index % 23 === 0 && tokens > 0
  return {
    date: isoDaysAgo(149 - index),
    ...totals(tokens, unknown ? null : (tokens / 300_000).toFixed(10), unknown ? 'unknown' : 'complete', tokens ? 1 : 0, unknown ? 1 : 0),
  }
}).filter((row) => row.totalTokens > 0)

const sessions = [
  { sessionId: 101, title: '我错过一期关于浏览器 Agent 的讨论', ...totals(4_800_000, '14.2000000000', 'partial', 1, 1) },
  { sessionId: 102, title: '排查会话编辑失效', ...totals(2_100_000, '6.4100000000', 'complete', 1) },
  { sessionId: 103, title: '实现工作区 MEMORY.md', ...totals(980_000, null, 'unknown', 1, 2) },
]

const dimensions = {
  providers: [
    { name: 'openrouter', ...totals(6_900_000, '20.6100000000', 'partial', 2, 1) },
    { name: 'dashscope', ...totals(980_000, null, 'unknown', 1, 2) },
  ],
  models: [
    { name: 'qwen/qwen3.6-27b', ...totals(4_800_000, '14.2000000000', 'partial', 1, 1) },
    { name: 'qwen/qwen3-coder', ...totals(3_080_000, '6.4100000000', 'partial', 2, 2) },
  ],
  tokenTypes: {
    input: 5_200_000,
    output: 2_680_000,
    cacheRead: 1_900_000,
    cacheWrite: 310_000,
    reasoning: 820_000,
    total: 7_880_000,
  },
}

const calls = [
  {
    id: 1,
    runId: 701,
    callId: 'planner:1',
    callKind: 'planner',
    provider: 'openrouter',
    model: 'qwen/qwen3.6-27b',
    inputTokens: 620000,
    outputTokens: 180000,
    cacheReadTokens: 130000,
    cacheWriteTokens: null,
    reasoningTokens: 32000,
    totalTokens: 800000,
    costUsd: '2.8100000000',
    costSource: 'provider',
    pricingVersion: null,
    startedAt: `${isoDaysAgo(1)}T08:30:00`,
    completedAt: `${isoDaysAgo(1)}T08:31:00`,
  },
  {
    id: 2,
    runId: 702,
    callId: 'memory:extract',
    callKind: 'memory_extractor',
    provider: 'dashscope',
    model: 'qwen/qwen3-coder',
    inputTokens: 18000,
    outputTokens: 4200,
    cacheReadTokens: null,
    cacheWriteTokens: null,
    reasoningTokens: null,
    totalTokens: 22200,
    costUsd: null,
    costSource: 'unknown',
    pricingVersion: null,
    startedAt: `${isoDaysAgo(0)}T03:20:00`,
    completedAt: `${isoDaysAgo(0)}T03:20:10`,
  },
]

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true })
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })
  const consoleErrors = []
  const failedResponses = []
  const requests = []
  let scenario = 'populated'
  let firstDailyRequest = true
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  page.on('response', (response) => {
    if (response.status() >= 400) failedResponses.push(`${response.status()} ${response.url()}`)
  })

  try {
    await page.route('**/api/v1/ai-assistant/sessions/999/runs', (route) =>
      fulfill(route, { list: [], total: 0 }),
    )
    await page.route('**/api/v1/ai-assistant/sessions', async (route) => {
      if (route.request().method() === 'POST') {
        return fulfill(route, { id: 999, title: 'UAT', status: 'ACTIVE' })
      }
      return fulfill(route, { list: [], total: 0 })
    })
    await page.route('**/api/v1/ai-assistant/usage/**', async (route) => {
      const url = new URL(route.request().url())
      requests.push(`${url.pathname}${url.search}`)
      if (url.pathname.endsWith('/usage/summary')) {
        if (scenario === 'error') {
          return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ code: 500, message: '模拟用量 API 失败', data: null }),
          })
        }
        return fulfill(route, scenario === 'empty' ? emptySummary : summary)
      }
      if (url.pathname.endsWith('/usage/daily')) {
        if (firstDailyRequest) {
          firstDailyRequest = false
          await new Promise((resolve) => setTimeout(resolve, 180))
        }
        const rows = scenario === 'empty' ? [] : daily
        return fulfill(route, { list: rows, total: rows.length, from: isoDaysAgo(364), to: isoDaysAgo(0) })
      }
      if (url.pathname.endsWith('/usage/sessions')) {
        const rows = scenario === 'empty' ? [] : sessions
        return fulfill(route, { list: rows, total: rows.length, limit: 50, offset: 0 })
      }
      if (url.pathname.endsWith('/usage/dimensions')) {
        return fulfill(
          route,
          scenario === 'empty'
            ? { providers: [], models: [], tokenTypes: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, reasoning: 0, total: 0 } }
            : dimensions,
        )
      }
      if (/\/usage\/sessions\/\d+$/.test(url.pathname)) {
        const selected = sessions.find((item) => url.pathname.endsWith(`/${item.sessionId}`)) || sessions[0]
        return fulfill(route, {
          ...selected,
          callCount: calls.length,
          calls,
          sessionDeleted: false,
          limit: 100,
          offset: 0,
        })
      }
      return route.abort()
    })

    await page.goto(`${baseUrl}/ai-assistant`, { waitUntil: 'domcontentloaded' })
    await page.getByTestId('ai-assistant-usage-entry').click()
    await page.waitForURL('**/ai-assistant/usage')
    await page.getByTestId('ai-assistant-usage-dashboard').waitFor({ timeout: 10000 })
    await page.getByTestId('ai-assistant-usage-loading').waitFor({ timeout: 10000 })
    await page.getByText('2.0B tokens').waitFor({ timeout: 10000 })

    const cards = await page.getByTestId('ai-assistant-usage-summary').locator('article').count()
    const heatmapCells = await page.getByTestId('ai-assistant-usage-heatmap').locator('.heatmap-cell[data-date]').count()
    assert(cards === 4, `expected four summary cards, got ${cards}`)
    assert(heatmapCells === 365, `expected 365 heatmap days, got ${heatmapCells}`)
    assert(await page.getByTestId('ai-assistant-usage-unknown-cost').isVisible(), 'unknown-cost state missing')

    await page.getByTestId('ai-assistant-usage-metric-toggle').getByText('Cost').click()
    assert(
      (await page.getByTestId('ai-assistant-usage-heatmap').locator('.heatmap-cell.unknown').count()) > 0,
      'cost heatmap should mark unknown-price days',
    )
    await page.screenshot({ path: screenshotPath })

    await page.getByTestId('ai-assistant-usage-sessions').getByText(sessions[0].title).click()
    await page.getByTestId('ai-assistant-usage-session-detail').waitFor({ timeout: 10000 })
    await page.getByTestId('ai-assistant-usage-session-detail').getByText('价格未知').waitFor()
    await page.getByTestId('ai-assistant-usage-session-detail').scrollIntoViewIfNeeded()
    await page.screenshot({ path: detailScreenshotPath })

    const evidence = await page.evaluate(() => ({
      title: document.querySelector('[data-testid="ai-assistant-usage-dashboard"] h1')?.textContent,
      summary: document.querySelector('[data-testid="ai-assistant-usage-summary"]')?.textContent,
      range: document.querySelector('[data-testid="ai-assistant-usage-range"]')?.textContent,
      sessionDetail: document.querySelector('[data-testid="ai-assistant-usage-session-detail"]')?.textContent,
      providerDistribution: document.querySelector('[data-testid="ai-assistant-usage-providers"]')?.textContent,
      modelDistribution: document.querySelector('[data-testid="ai-assistant-usage-models"]')?.textContent,
      tokenTypes: document.querySelector('[data-testid="ai-assistant-usage-token-types"]')?.textContent,
    }))
    assert(consoleErrors.length === 0, `success-state console errors: ${consoleErrors.join(' | ')} responses=${failedResponses.join(' | ')}`)
    const successConsoleErrors = [...consoleErrors]

    scenario = 'empty'
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.getByTestId('ai-assistant-usage-empty').waitFor({ timeout: 10000 })
    const emptyState = await page.getByTestId('ai-assistant-usage-empty').textContent()

    scenario = 'error'
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.getByTestId('ai-assistant-usage-error').waitFor({ timeout: 10000 })
    const errorState = await page.getByTestId('ai-assistant-usage-error').textContent()
    const expectedErrorConsole = [...consoleErrors]
    consoleErrors.length = 0

    scenario = 'populated'
    await page.getByTestId('ai-assistant-usage-error').getByText('重试').click()
    await page.getByText('2.0B tokens').waitFor({ timeout: 10000 })

    fs.writeFileSync(
      evidencePath,
      `${JSON.stringify({ ...evidence, emptyState, errorState, cards, heatmapCells, requests, successConsoleErrors, expectedErrorConsole, recoveryConsoleErrors: consoleErrors, screenshotPath, detailScreenshotPath }, null, 2)}\n`,
    )
    assert(consoleErrors.length === 0, `recovery console errors: ${consoleErrors.join(' | ')}`)
    assert(requests.some((request) => request.includes('limit=50')), 'session pagination query missing')
    assert(requests.every((request) => request.includes('timezone=')), 'timezone query missing')
    console.log(`PASS AI Assistant usage UAT cards=${cards} heatmapDays=${heatmapCells} detailCalls=${calls.length} states=loading,empty,error,recovered`)
    console.log(`screenshot=${screenshotPath}`)
    console.log(`detailScreenshot=${detailScreenshotPath}`)
    console.log(`evidence=${evidencePath}`)
  } finally {
    await browser.close()
  }
}

await run()
