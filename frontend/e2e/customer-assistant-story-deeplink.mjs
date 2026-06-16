import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT || ''
const reportPath = process.env.HIFY_E2E_REPORT || ''
const demoHostContext = {
  actorId: 'mvp-demo-operator',
  actorName: 'MVP Demo Operator',
  tenantId: 'mvp-demo-tenant',
  orgId: 'mvp-demo-org',
  roles: ['customer_service_operator'],
  permissions: ['customer_assistant:read', 'customer_assistant:operate'],
  source: 'mvp-demo-shell',
  locale: 'zh-CN',
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function api(page, path) {
  const response = await page.request.get(`${baseUrl}/api/v1${path}`)
  assert(response.ok(), `${path} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${path} API ${payload.message}`)
  return payload.data
}

async function waitForStory(page, story) {
  await page.getByText(/Session #/).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText(story.customerName).first().waitFor({ state: 'visible', timeout: 10000 })
  await page
    .getByTestId('customer-conversation-lane')
    .getByText(story.openingMessage)
    .waitFor({ state: 'visible', timeout: 10000 })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const report = { baseUrl, selected: [] }

try {
  await page.addInitScript((hostContext) => {
    globalThis.__HIFY_HOST__ = {
      ...hostContext,
      apiBaseUrl: '/api',
    }
  }, demoHostContext)

  const stories = await api(page, '/customer-assistant/demo-stories')
  assert(stories.list.length >= 2, `Expected at least two seeded stories, got ${stories.list.length}`)
  const metrics = await api(page, '/customer-assistant/demo-stories/metrics')
  assert(metrics.storyCount >= stories.list.length, `Expected metrics story count to cover stories, got ${metrics.storyCount}`)
  assert(metrics.sessionCount >= stories.list.length, `Expected metrics session count to cover stories, got ${metrics.sessionCount}`)
  assert(metrics.humanConfirmation.pending >= 1, 'Expected seeded demo metrics to include pending confirmations')
  const first = stories.list[0]
  const second = stories.list[1]

  await page.goto(`${baseUrl}/customer-assistant?view=demo&story=${encodeURIComponent(second.storyId)}`, {
    waitUntil: 'networkidle',
  })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  const demoMetrics = page.getByTestId('customer-assistant-demo-metrics')
  await demoMetrics.getByText('演示总览').waitFor({ state: 'visible', timeout: 10000 })
  await demoMetrics.getByText(new RegExp(`${metrics.storyCount} 条故事`)).waitFor({ state: 'visible', timeout: 10000 })
  await demoMetrics.getByText('人工采纳率').waitFor({ state: 'visible', timeout: 10000 })
  await demoMetrics.getByText('待确认动作').waitFor({ state: 'visible', timeout: 10000 })
  await waitForStory(page, second)
  let url = new URL(page.url())
  assert(url.searchParams.get('story') === second.storyId, `Expected story query ${second.storyId}, got ${url}`)
  assert(url.searchParams.get('view') === 'demo', `Expected unrelated view query to be preserved, got ${url}`)
  report.selected.push({ storyId: second.storyId, via: 'query' })

  const storyStrip = page.getByTestId('customer-assistant-demo-stories')
  await storyStrip.getByRole('button', { name: new RegExp(escapeRegExp(first.title)) }).click()
  await waitForStory(page, first)
  url = new URL(page.url())
  assert(url.searchParams.get('story') === first.storyId, `Expected story query ${first.storyId}, got ${url}`)
  assert(url.searchParams.get('view') === 'demo', `Expected view query to remain after switch, got ${url}`)
  report.selected.push({ storyId: first.storyId, via: 'switch' })

  const pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    bodyLength: document.body.innerText.trim().length,
  }))
  assert(pageMetrics.overflowX <= 0, `Expected no horizontal overflow, got ${pageMetrics.overflowX}`)
  assert(pageMetrics.bodyLength > 0, 'Expected visible body text')
  report.pageMetrics = pageMetrics

  if (screenshotPath) {
    mkdirSync(dirname(screenshotPath), { recursive: true })
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  if (reportPath) {
    mkdirSync(dirname(reportPath), { recursive: true })
    writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  }

  console.log('PASS customer assistant story deeplink e2e')
} finally {
  await browser.close()
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
