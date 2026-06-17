import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const __dirname = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(__dirname, '../..')
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR
  || join(repoRoot, 'artifacts/slices/121-customer-assistant-session-inbox-dashboard/121.1')
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || join(artifactDir, 'screenshots')
const reportPath = process.env.HIFY_E2E_REPORT || join(artifactDir, 'uat-report.json')
const notesPath = process.env.HIFY_E2E_NOTES || join(artifactDir, 'uat.md')
const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'

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

async function waitForSession(page, story) {
  await page.getByText(`Session #${story.sessionId}`).first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('customer-conversation-lane').getByText(story.openingMessage).waitFor({
    state: 'visible',
    timeout: 10000,
  })
}

async function selectInboxStory(page, story) {
  const inbox = page.getByTestId('operator-session-inbox-dashboard')
  const row = inbox
    .getByTestId('operator-session-inbox-row')
    .filter({ hasText: `Session #${story.sessionId}` })
    .first()
  await row.getByText(story.customerName).waitFor({ state: 'visible', timeout: 10000 })
  await row.getByText(story.title).waitFor({ state: 'visible', timeout: 10000 })
  await row.click()
  await waitForSession(page, story)
  return row
}

function writeReport(report) {
  mkdirSync(dirname(reportPath), { recursive: true })
  writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  writeFileSync(
    notesPath,
    [
      '# UAT Notes',
      '',
      `Base URL: ${report.baseUrl}`,
      '',
      'Verified:',
      `- Seeded sessions visible: ${report.visibleSessions}`,
      `- First selected: ${report.switches[0].storyId} / session ${report.switches[0].sessionId}`,
      `- Second selected: ${report.switches[1].storyId} / session ${report.switches[1].sessionId}`,
      `- Horizontal overflow: ${report.pageMetrics.overflowX}`,
      '',
      'Screenshots:',
      ...report.screenshots.map((path) => `- ${path}`),
      '',
    ].join('\n'),
  )
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const report = {
  baseUrl,
  visibleSessions: 0,
  switches: [],
  screenshots: [],
  pageMetrics: null,
}

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
  assert(metrics.stories.length >= 2, `Expected per-story metrics for inbox rows, got ${metrics.stories.length}`)

  const first = stories.list[0]
  const second = stories.list[1]

  await page.goto(`${baseUrl}/customer-assistant?view=demo&story=${encodeURIComponent(first.storyId)}`, {
    waitUntil: 'networkidle',
  })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  const inbox = page.getByTestId('operator-session-inbox-dashboard')
  await inbox.getByText('多客户会话').waitFor({ state: 'visible', timeout: 10000 })
  await inbox.getByTestId('operator-session-inbox-row').nth(1).waitFor({ state: 'visible', timeout: 10000 })

  const inboxText = await inbox.innerText()
  for (const story of stories.list.slice(0, 2)) {
    assert(inboxText.includes(story.customerName), `Inbox missing customer ${story.customerName}`)
    assert(inboxText.includes(story.title), `Inbox missing story ${story.title}`)
    assert(inboxText.includes(`Session #${story.sessionId}`), `Inbox missing session ${story.sessionId}`)
  }
  assert(
    ['活跃处理', '待确认动作', '阻塞等待', '完成归档'].some((label) => inboxText.includes(label)),
    'Inbox missing status hints',
  )
  report.visibleSessions = await inbox.getByTestId('operator-session-inbox-row').count()

  await selectInboxStory(page, first)
  report.switches.push({ storyId: first.storyId, sessionId: first.sessionId })
  let url = new URL(page.url())
  assert(url.searchParams.get('story') === first.storyId, `Expected story query ${first.storyId}, got ${url}`)

  const secondRow = await selectInboxStory(page, second)
  await secondRow.evaluate((element) => {
    if (!element.classList.contains('selected')) {
      throw new Error('Selected inbox row did not receive selected state')
    }
  })
  report.switches.push({ storyId: second.storyId, sessionId: second.sessionId })
  url = new URL(page.url())
  assert(url.searchParams.get('story') === second.storyId, `Expected story query ${second.storyId}, got ${url}`)

  const customerLane = page.getByTestId('customer-conversation-lane')
  assert(
    !(await customerLane.getByText('多客户会话').count()),
    'Session inbox dashboard leaked into customer lane',
  )

  report.pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    bodyLength: document.body.innerText.trim().length,
  }))
  assert(report.pageMetrics.overflowX <= 0, `Expected no horizontal overflow, got ${report.pageMetrics.overflowX}`)
  assert(report.pageMetrics.bodyLength > 0, 'Expected visible body text')

  mkdirSync(screenshotDir, { recursive: true })
  const screenshotPath = join(screenshotDir, 'session-inbox-dashboard.png')
  await page.screenshot({ path: screenshotPath, fullPage: true })
  report.screenshots.push(screenshotPath)
  writeReport(report)

  console.log('PASS customer assistant session inbox dashboard uat')
} finally {
  await browser.close()
}
