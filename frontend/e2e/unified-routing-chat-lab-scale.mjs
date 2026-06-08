import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5175/runtime-lab/chat'
const artifactSlice = process.env.HIFY_E2E_ARTIFACT_SLICE || '034.6'
const chatflowBound = process.env.HIFY_E2E_CHATFLOW_BOUND === '1'
const artifactDir = resolve(process.cwd(), `artifacts/slices/034-unified-routing-chat-lab/${artifactSlice}`)
const screenshotPath = resolve(artifactDir, 'browser-uat-unified-routing-chat-lab-scale.png')
const reportPath = resolve(artifactDir, 'browser-uat.md')

const scenarios = [
  {
    label: '机票预订',
    sopId: 'flight_booking',
    start: '我想买一张明天上午从北京去上海的机票，时间最好别太早',
    collect: '手机号 13800138010，乘机人陈测试',
  },
  {
    label: '票价咨询',
    sopId: 'fare_quote',
    start: '我先不出票，想问下北京到上海今天票价大概多少',
    collect: '订单号 CA0134，手机号 13800138011，乘机人蒋测试',
  },
  {
    label: '团队订票',
    sopId: 'group_booking',
    start: '我们公司十六个人出差，想咨询团队机票怎么订',
    collect: '订单号 CA0234，手机号 13800138012，乘机人沈测试',
  },
  {
    label: '增值服务',
    sopId: 'ancillary_sales',
    start: '买完票以后还能加购餐食和贵宾厅吗？',
    collect: '订单号 CA0334，手机号 13800138013，乘机人韩测试',
  },
  {
    label: '退票办理',
    sopId: 'refund_ticket',
    start: '您好，我临时出差取消了，想把今晚这张机票退掉，麻烦帮我看看退票规则',
    collect: '订单号：CA1034，手机号：13800138000，乘机人张测试',
  },
  {
    label: '改签办理',
    sopId: 'change_flight',
    start: '我明天会议提前，想把航班改签到更早一班',
    collect: '订单号 CA2034，手机号 13800138001，乘机人李测试',
  },
  {
    label: '资料修改',
    sopId: 'passenger_info_change',
    start: '我证件号填错了一位，想修改乘机人信息',
    collect: '订单号 CA2134，手机号 13800138014，乘机人许测试',
  },
  {
    label: '发票申请',
    sopId: 'invoice_apply',
    start: '公司报销要凭证，帮我开一下电子发票',
    collect: '订单号 CA3034，手机号 13800138002，乘机人王测试',
  },
  {
    label: '行李服务',
    sopId: 'baggage_service',
    start: '我带了两个箱子，想加购托运行李额',
    collect: '订单号 CA4034，手机号 13800138003，乘机人赵测试',
  },
  {
    label: '值机选座',
    sopId: 'seat_checkin',
    start: '我想线上值机，最好选靠窗座位',
    collect: '订单号 CA5034，手机号 13800138004，乘机人钱测试',
  },
  {
    label: '航班动态',
    sopId: 'flight_status',
    start: '我想查一下今天航班动态，听说天气不好',
    collect: '订单号 CA6034，手机号 13800138005，乘机人孙测试',
  },
  {
    label: '特殊协助',
    sopId: 'special_assistance',
    start: '老人第一次坐飞机，需要轮椅协助',
    collect: '订单号 CA7034，手机号 13800138006，乘机人周测试',
  },
  {
    label: '宠物乘机',
    sopId: 'pet_cabin',
    start: '我想带猫坐飞机，问下宠物进客舱要求',
    collect: '订单号 CA8034，手机号 13800138007，乘机人吴测试',
  },
  {
    label: '异常航班',
    sopId: 'irregular_flight',
    start: '航班取消了，我需要改签或补偿方案',
    collect: '订单号 CA9034，手机号 13800138008，乘机人郑测试',
  },
  {
    label: '会员里程',
    sopId: 'membership_service',
    start: '我的会员里程没到账，帮我补登一下',
    collect: '订单号 CA1134，手机号 13800138009，乘机人冯测试',
  },
]

const switchJourneys = [
  ['refund_ticket', 'flight_status'],
  ['change_flight', 'special_assistance'],
  ['invoice_apply', 'membership_service'],
  ['baggage_service', 'pet_cabin'],
  ['seat_checkin', 'irregular_flight'],
].map(([primary, secondary]) => ({
  primary: scenarios.find((item) => item.sopId === primary),
  secondary: scenarios.find((item) => item.sopId === secondary),
}))

mkdirSync(artifactDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const consoleMessages = []
const failedResponses = []

page.on('console', (message) => {
  if (message.type() === 'error') consoleMessages.push(message.text())
})
page.on('response', (response) => {
  if (response.url().includes('/api/') && response.status() >= 400) {
    failedResponses.push(`${response.status()} ${response.url()}`)
  }
})

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-lab-chat').waitFor({ timeout: 15_000 })
  await expectScenarioCatalog(page)

  const completedScenarios = []
  for (const scenario of scenarios) {
    await runCompleteScenario(page, scenario)
    completedScenarios.push(scenario.sopId)
  }

  const completedSwitches = []
  for (const journey of switchJourneys) {
    await runSwitchResumeJourney(page, journey)
    completedSwitches.push(`${journey.primary.sopId}->${journey.secondary.sopId}`)
  }

  await page.screenshot({ path: screenshotPath, fullPage: true })

  const routeAction = await page.getByTestId('route-action').innerText()
  const report = [
    `# Browser UAT: Unified Routing Chat Lab ${artifactSlice}`,
    '',
    `- URL: ${baseUrl}`,
    `- Chatflow-bound refund SOP: ${chatflowBound ? 'yes' : 'no'}`,
    `- SOP catalog count: ${scenarios.length}`,
    `- Completed scenario journeys: ${completedScenarios.join(', ')}`,
    `- Switch/resume journeys: ${completedSwitches.join(', ')}`,
    '- Expected actions: START_SOP, SUSPEND_AND_START, CONTINUE_ACTIVE_SOP, COMPLETE_TASK, RESUME_TASK',
    `- Final route action: ${routeAction}`,
    `- Screenshot: ${screenshotPath}`,
    `- Console errors: ${consoleMessages.length ? consoleMessages.join(' | ') : 'none'}`,
    `- Failed API responses: ${failedResponses.length ? failedResponses.join(' | ') : 'none'}`,
    '',
  ].join('\n')
  writeFileSync(reportPath, report)
  console.log(`Unified routing chat lab scale UAT passed: ${completedScenarios.length} scenarios, ${completedSwitches.length} switches`)
} finally {
  await browser.close()
}

async function expectScenarioCatalog(page) {
  await page.locator('.sop-option').last().waitFor({ timeout: 15_000 })
  const count = await page.locator('.sop-option').count()
  assert(count === scenarios.length, `Expected ${scenarios.length} SOP options, got ${count}`)
  for (const scenario of scenarios) {
    await page.locator('.sop-option').filter({ hasText: scenario.label }).waitFor({ timeout: 15_000 })
  }
}

async function runCompleteScenario(page, scenario) {
  await createFreshSession(page)
  await sendTurn(page, scenario.start)
  await waitForRouteAction(page, 'START_SOP')
  await expectTaskStatus(page, scenario.sopId, 'RUNNING')
  if (chatflowBound && scenario.sopId === 'refund_ticket') {
    await page.getByText('请补充订单号和手机号').last().waitFor({ timeout: 15_000 })
  }

  await sendTurn(page, scenario.collect)
  await waitForRouteAction(page, 'CONTINUE_ACTIVE_SOP')
  await page.getByText(/请回复 confirm|请确认是否继续办理/).last().waitFor({ timeout: 15_000 })

  await sendTurn(page, '确认，按这个方案办理')
  await waitForRouteAction(page, 'COMPLETE_TASK')
  await expectTaskStatus(page, scenario.sopId, 'COMPLETED')
}

async function runSwitchResumeJourney(page, journey) {
  await createFreshSession(page)
  await sendTurn(page, journey.primary.start)
  await waitForRouteAction(page, 'START_SOP')
  await expectTaskStatus(page, journey.primary.sopId, 'RUNNING')

  await sendTurn(page, journey.secondary.start)
  await waitForRouteAction(page, 'SUSPEND_AND_START')
  await expectTaskStatus(page, journey.primary.sopId, 'SUSPENDED')
  await expectTaskStatus(page, journey.secondary.sopId, 'RUNNING')

  await sendTurn(page, journey.secondary.collect)
  await waitForRouteAction(page, 'CONTINUE_ACTIVE_SOP')
  await sendTurn(page, '确认')
  await waitForRouteAction(page, 'COMPLETE_TASK')
  await expectTaskStatus(page, journey.secondary.sopId, 'COMPLETED')

  await sendTurn(page, '继续')
  await waitForRouteAction(page, 'RESUME_TASK')
  await expectTaskStatus(page, journey.primary.sopId, 'RUNNING')

  await sendTurn(page, journey.primary.collect)
  await waitForRouteAction(page, 'CONTINUE_ACTIVE_SOP')
  await sendTurn(page, '确认')
  await waitForRouteAction(page, 'COMPLETE_TASK')
  await expectTaskStatus(page, journey.primary.sopId, 'COMPLETED')
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

async function expectTaskStatus(page, sopId, status) {
  await page.locator('.task-row').filter({ hasText: sopId }).filter({ hasText: status }).last().waitFor({
    timeout: 15_000,
  })
}

async function sendTurn(page, message) {
  await page.getByTestId('runtime-lab-input').fill(message)
  await page.getByTestId('runtime-lab-send').click()
}

async function waitForRouteAction(page, action) {
  await page.getByTestId('route-action').filter({ hasText: action }).waitFor({ timeout: 15_000 })
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}
