import { mkdir } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function intersects(a, b) {
  const x = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left))
  const y = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top))
  return x * y
}

function envelope(data) {
  return { code: 200, message: 'success', data }
}

const pendingAction = {
  id: 9,
  sessionId: 12,
  runId: 31,
  taskId: 101,
  actionKey: 'refund_ticket:submit_refund:TK-100',
  actionType: 'submit_refund',
  title: '提交退票申请',
  payload: { orderNo: 'TK-100' },
  status: 'PENDING',
}

const turnResult = {
  runId: 31,
  sessionId: 12,
  replyType: 'DRAFT',
  operatorRecommendation: 'Operator recommendations:\n- 已识别退票任务，请继续确认订单。',
  customerReplyDraft: '已为您查询订单 TK-100，请确认是否提交退票申请。',
  taskSummaries: [
    {
      id: 101,
      sessionId: 12,
      taskKey: 'refund_ticket',
      taskType: 'refund',
      businessKey: 'refund_ticket',
      shortId: 'refund-101',
      status: 'COMPLETED',
      workerType: 'chatflow_sop',
      workerRef: 'refund_ticket',
      checkpoint: { currentStep: 'completed' },
      lastResult: { status: 'COMPLETED' },
      proposedActions: [pendingAction],
      version: 1,
    },
  ],
  proposedActions: [pendingAction],
  warnings: [],
  events: [],
  replayed: false,
}

const viewports = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'narrow', width: 390, height: 900 },
]

const browser = await chromium.launch()
const page = await browser.newPage()

try {
  if (screenshotDir) await mkdir(screenshotDir, { recursive: true })

  await page.route('**/api/v1/customer-assistant/**', async (route) => {
    const request = route.request()
    const url = request.url()
    const method = request.method()

    if (method === 'POST' && url.endsWith('/sessions')) {
      await route.fulfill({ json: envelope({ id: 12, status: 'ACTIVE', context: {} }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/12/turns')) {
      await route.fulfill({ json: envelope(turnResult) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/tasks')) {
      await route.fulfill({ json: envelope({ list: turnResult.taskSummaries, total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/events')) {
      await route.fulfill({ json: envelope({ list: turnResult.events, total: 0 }) })
      return
    }
    await route.fulfill({ status: 404, json: { code: 404, message: 'unexpected call', data: null } })
  })

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
    await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
    await page.getByTestId('operator-action-empty-state').waitFor({ state: 'visible', timeout: 10000 })
    await page.getByRole('button', { name: '模拟客户输入' }).click()
    await page.getByLabel('确认拟议动作').waitFor({ state: 'visible', timeout: 10000 })

    for (const testId of [
      'customer-conversation-lane',
      'operator-conversation-lane',
      'operator-task-ledger',
      'operator-recommendation-panel',
      'operator-draft-panel',
      'operator-proposed-actions-panel',
      'operator-event-timeline',
      'operator-warnings-panel',
    ]) {
      assert(await page.getByTestId(testId).isVisible(), `${viewport.name}: expected ${testId} visible`)
    }

    const metrics = await page.evaluate(() => {
      const ids = [
        'customer-conversation-lane',
        'operator-conversation-lane',
        'operator-task-ledger',
        'operator-recommendation-panel',
        'operator-draft-panel',
        'operator-proposed-actions-panel',
        'operator-event-timeline',
        'operator-warnings-panel',
      ]
      const boxes = ids.map((id) => {
        const rect = document.querySelector(`[data-testid="${id}"]`).getBoundingClientRect()
        return { id, top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left }
      })
      const actionButtons = Array.from(
        document.querySelectorAll('[aria-label="确认拟议动作"], [aria-label="拒绝拟议动作"]'),
      ).map((button) => {
        const rect = button.getBoundingClientRect()
        return { width: rect.width, height: rect.height }
      })
      return {
        boxes,
        actionButtons,
        overflowX: document.documentElement.scrollWidth - window.innerWidth,
      }
    })

    assert(metrics.overflowX <= 0, `${viewport.name}: expected no horizontal overflow, got ${metrics.overflowX}`)
    assert(metrics.actionButtons.length === 2, `${viewport.name}: expected confirm/reject action controls`)
    assert(
      metrics.actionButtons.every((button) => button.width > 0 && button.height > 0),
      `${viewport.name}: expected action controls to have stable visible dimensions`,
    )
    for (let i = 0; i < metrics.boxes.length; i += 1) {
      for (let j = i + 1; j < metrics.boxes.length; j += 1) {
        const area = intersects(metrics.boxes[i], metrics.boxes[j])
        assert(area < 1, `${viewport.name}: ${metrics.boxes[i].id} overlaps ${metrics.boxes[j].id}`)
      }
    }

    if (screenshotDir) {
      await page.screenshot({ path: join(screenshotDir, `${viewport.name}.png`), fullPage: true })
    }
  }

  console.log('PASS customer assistant responsive e2e')
} finally {
  await browser.close()
}
