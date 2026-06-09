import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5175/runtime-lab/chat'
const artifactSlice = process.env.HIFY_E2E_ARTIFACT_SLICE || '034.3'
const artifactDir = resolve(process.cwd(), `artifacts/slices/034-unified-routing-chat-lab/${artifactSlice}`)
const screenshotPath = resolve(artifactDir, 'browser-uat-unified-routing-chat-lab.png')
const reportPath = resolve(artifactDir, 'browser-uat.md')

const interruptJourneys = [
  {
    name: 'refund-to-invoice-resume',
    primaryLabel: '退票办理',
    primaryTask: 'refund_ticket',
    primaryStart: '您好，我临时出差取消了，想把今晚这张机票退掉',
    switchLabel: '发票申请',
    switchTask: 'invoice_apply',
    switchStart: '公司报销要凭证，帮我开一下电子发票',
    switchConfirm: '确认开票',
  },
  {
    name: 'change-to-baggage-resume',
    primaryLabel: '改签办理',
    primaryTask: 'change_flight',
    primaryStart: '我明天会议提前，想把航班改签到更早一班',
    switchLabel: '行李服务',
    switchTask: 'baggage_service',
    switchStart: '我带了两个箱子，想加购托运行李额',
    switchConfirm: '确认加购行李',
  },
  {
    name: 'seat-to-refund-resume',
    primaryLabel: '值机选座',
    primaryTask: 'seat_checkin',
    primaryStart: '我想线上值机，最好选靠窗座位',
    switchLabel: '退票办理',
    switchTask: 'refund_ticket',
    switchStart: '我不飞了，票款能不能退回来？',
    switchConfirm: '确认退票',
  },
]

mkdirSync(artifactDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const consoleMessages = []

page.on('console', (message) => {
  if (message.type() === 'error') consoleMessages.push(message.text())
})

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-lab-chat').waitFor({ timeout: 15_000 })

  const passedJourneys = []
  for (const journey of interruptJourneys) {
    await runInterruptResumeJourney(page, journey)
    passedJourneys.push(journey.name)
  }

  await runNonInterruptibleRejection(page)
  passedJourneys.push('confirm-step-reject-switch')

  await page.screenshot({ path: screenshotPath, fullPage: true })

  const routeAction = await page.getByTestId('route-action').innerText()
  const report = [
    '# Browser UAT: Unified Routing Chat Lab',
    '',
    `- URL: ${baseUrl}`,
    `- Artifact slice: ${artifactSlice}`,
    `- Journeys: ${passedJourneys.join(', ')}`,
    '- Expected interrupt actions per journey: START_SOP, SUSPEND_AND_START, CONTINUE_ACTIVE_SOP, COMPLETE_TASK, RESUME_TASK',
    '- Expected rejection action: REJECT_SWITCH_CONTINUE_ACTIVE',
    `- Final route action: ${routeAction}`,
    `- Screenshot: ${screenshotPath}`,
    `- Console errors: ${consoleMessages.length ? consoleMessages.join(' | ') : 'none'}`,
    '',
  ].join('\n')
  writeFileSync(reportPath, report)
  console.log(`Unified routing chat lab UAT passed: ${passedJourneys.length} journeys, final ${routeAction}`)
} finally {
  await browser.close()
}

async function runInterruptResumeJourney(page, journey) {
  await createFreshSession(page)
  await selectSop(page, journey.primaryLabel)
  await sendTurn(page, journey.primaryStart)
  await waitForRouteAction(page, 'START_SOP')
  await expectTaskStatus(page, journey.primaryTask, 'RUNNING')

  await selectSop(page, journey.switchLabel)
  await sendTurn(page, journey.switchStart)
  await waitForRouteAction(page, 'SUSPEND_AND_START')
  await expectTaskStatus(page, journey.primaryTask, 'SUSPENDED')
  await expectTaskStatus(page, journey.switchTask, 'RUNNING')

  await sendTurn(page, '订单号 TK001，手机号 13800138000，乘机人张测试')
  await waitForRouteAction(page, 'CONTINUE_ACTIVE_SOP')

  await sendTurn(page, journey.switchConfirm)
  await waitForRouteAction(page, 'COMPLETE_TASK')
  await expectTaskStatus(page, journey.switchTask, 'COMPLETED')

  await sendTurn(page, '继续')
  await waitForRouteAction(page, 'RESUME_TASK')
  await expectTaskStatus(page, journey.primaryTask, 'RUNNING')
}

async function runNonInterruptibleRejection(page) {
  await createFreshSession(page)
  await selectSop(page, '退票办理')
  await sendTurn(page, '我要退票，但想先知道扣费')
  await waitForRouteAction(page, 'START_SOP')

  await sendTurn(page, '订单号 TK999，手机号 13800138000，乘机人张测试')
  await waitForRouteAction(page, 'CONTINUE_ACTIVE_SOP')

  await selectSop(page, '发票申请')
  await sendTurn(page, '我要开发票')
  await waitForRouteAction(page, 'REJECT_SWITCH_CONTINUE_ACTIVE')
  await page.getByText('当前步骤不能中断，请先完成确认后再切换。').last().waitFor({ timeout: 15_000 })
  await expectTaskStatus(page, 'refund_ticket', 'RUNNING')
}

async function createFreshSession(page) {
  const sessionLabel = page.locator('.session-id')
  const previousSession = await sessionLabel.innerText().catch(() => '')
  await page.getByRole('button', { name: '新会话' }).click()
  await page.waitForFunction(
    ({ previous }) => {
      const label = document.querySelector('.session-id')?.textContent || ''
      return /^#\d+$/.test(label.trim()) && label.trim() !== previous
    },
    { previous: previousSession.trim() },
    { timeout: 15_000 },
  )
}

async function selectSop(page, label) {
  await page.locator('.enabled-scope-chip').filter({ hasText: label }).waitFor({ timeout: 15_000 })
}

async function expectTaskStatus(page, sopId, status) {
  await page.locator('.task-row').filter({ hasText: sopId }).filter({ hasText: status }).last().waitFor({
    timeout: 45_000,
  })
}

async function sendTurn(page, message) {
  await page.getByTestId('runtime-lab-input').fill(message)
  await page.getByTestId('runtime-lab-send').click()
}

async function waitForRouteAction(page, action) {
  await page.getByTestId('route-action').filter({ hasText: action }).waitFor({ timeout: 45_000 })
}
