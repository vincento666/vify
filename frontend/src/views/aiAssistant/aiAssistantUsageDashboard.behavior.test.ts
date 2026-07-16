// @vitest-environment jsdom
import { createApp, nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  getAiAssistantUsageSummary: vi.fn(),
  getAiAssistantUsageDaily: vi.fn(),
  getAiAssistantUsageSessions: vi.fn(),
  getAiAssistantUsageDimensions: vi.fn(),
  getAiAssistantUsageSession: vi.fn(),
}))

vi.mock('@/api/aiAssistant', () => api)

import Dashboard from './AiAssistantUsageDashboard.vue'

const totals = (totalTokens = 10, costUsd: string | null = '0.1000000000', costState = 'complete') => ({
  totalTokens,
  costUsd,
  costState,
  unknownCostCount: costState === 'complete' ? 0 : 1,
  unknownCostTokens: costState === 'complete' ? 0 : totalTokens,
  sessionCount: totalTokens ? 1 : 0,
  callCount: totalTokens ? 1 : 0,
})

const summary = {
  today: totals(10),
  yesterday: totals(20),
  rolling30Days: totals(30, '0.2000000000', 'partial'),
  cumulative: totals(60, '0.3000000000', 'partial'),
}
const dimensions = {
  providers: [{ name: 'openrouter', ...totals(60) }],
  models: [{ name: 'qwen', ...totals(60) }],
  tokenTypes: { input: 40, output: 20, cacheRead: 0, cacheWrite: 0, reasoning: 0, total: 60 },
}
const firstSession = { sessionId: 1, title: 'First', ...totals(60) }
const secondSession = { sessionId: 2, title: 'Second', ...totals(40) }
const call = {
  id: 1,
  runId: 1,
  callId: 'planner:1',
  callKind: 'planner',
  provider: 'openrouter',
  model: 'qwen',
  inputTokens: 10,
  outputTokens: null,
  cacheReadTokens: null,
  cacheWriteTokens: null,
  reasoningTokens: null,
  totalTokens: null,
  costUsd: '0.0000000100',
  costSource: 'unknown',
  pricingVersion: null,
  startedAt: '2026-07-11T03:20:00',
  completedAt: '2026-07-11T03:20:01',
}

async function flushUi() {
  await Promise.resolve()
  await nextTick()
  await new Promise((resolve) => setTimeout(resolve, 0))
  await nextTick()
}

function mountDashboard() {
  const host = document.createElement('div')
  document.body.appendChild(host)
  const app = createApp(Dashboard)
  app.component('router-link', {
    props: ['to'],
    template: '<a :href="to"><slot /></a>',
  })
  app.mount(host)
  return { host, unmount: () => app.unmount() }
}

function configureSuccess() {
  api.getAiAssistantUsageSummary.mockResolvedValue(summary)
  api.getAiAssistantUsageDaily.mockResolvedValue({
    list: [{ date: '2026-07-11', ...totals(60, null, 'unknown') }],
    total: 1,
    from: '2025-07-12',
    to: '2026-07-11',
  })
  api.getAiAssistantUsageSessions.mockResolvedValue({ list: [firstSession], total: 1, limit: 50, offset: 0 })
  api.getAiAssistantUsageDimensions.mockResolvedValue(dimensions)
  api.getAiAssistantUsageSession.mockResolvedValue({
    ...firstSession,
    calls: [call],
    callCount: 1,
    sessionDeleted: false,
    limit: 100,
    offset: 0,
  })
}

beforeEach(() => {
  document.body.innerHTML = ''
  for (const mock of Object.values(api)) mock.mockReset()
  configureSuccess()
})

describe('AI Assistant usage dashboard behavior', () => {
  it('renders loading, toggles Cost, applies range, and drills through both pagination levels', async () => {
    let resolveSummary: (value: typeof summary) => void = () => undefined
    api.getAiAssistantUsageSummary.mockReturnValue(
      new Promise((resolve) => {
        resolveSummary = resolve
      }),
    )
    api.getAiAssistantUsageSessions
      .mockResolvedValueOnce({ list: [firstSession], total: 51, limit: 50, offset: 0 })
      .mockResolvedValueOnce({ list: [secondSession], total: 51, limit: 50, offset: 50 })
      .mockResolvedValue({ list: [firstSession], total: 1, limit: 50, offset: 0 })
    api.getAiAssistantUsageSession.mockResolvedValue({
      ...secondSession,
      calls: [call],
      callCount: 101,
      sessionDeleted: false,
      limit: 100,
      offset: 0,
    })

    const { host, unmount } = mountDashboard()
    expect(host.querySelector('[data-testid="ai-assistant-usage-loading"]')).not.toBeNull()
    resolveSummary(summary)
    await flushUi()

    const costButton = Array.from(host.querySelectorAll('button')).find((button) => button.textContent === 'Cost')!
    costButton.click()
    await nextTick()
    expect(costButton.getAttribute('aria-pressed')).toBe('true')

    const inputs = host.querySelectorAll<HTMLInputElement>('input[type="date"]')
    inputs[0].value = '2026-07-01'
    inputs[0].dispatchEvent(new Event('input', { bubbles: true }))
    inputs[1].value = '2026-07-11'
    inputs[1].dispatchEvent(new Event('input', { bubbles: true }))

    const sessionNext = host.querySelector('[data-testid="ai-assistant-usage-session-pagination"] button:last-child') as HTMLButtonElement
    sessionNext.click()
    await flushUi()
    expect(api.getAiAssistantUsageSessions).toHaveBeenLastCalledWith(expect.any(Object), { limit: 50, offset: 50 })
    const lastSessionCall = api.getAiAssistantUsageSessions.mock.calls[
      api.getAiAssistantUsageSessions.mock.calls.length - 1
    ]
    expect(lastSessionCall[0].from).not.toBe('2026-07-01')

    const sessionButton = Array.from(host.querySelectorAll('.session-row')).find((button) => button.textContent?.includes('Second')) as HTMLButtonElement
    sessionButton.click()
    await flushUi()
    expect(host.querySelector('[data-testid="ai-assistant-usage-session-detail"]')?.textContent).toContain('Token 未知')
    expect(host.querySelector('[data-testid="ai-assistant-usage-session-detail"]')?.textContent).toContain('<$0.0001')
    const callNext = host.querySelector('[data-testid="ai-assistant-usage-call-pagination"] button:last-child') as HTMLButtonElement
    callNext.click()
    await flushUi()
    expect(api.getAiAssistantUsageSession).toHaveBeenLastCalledWith(2, expect.any(Object), { limit: 100, offset: 100 })

    let rejectStaleDetail: (reason: Error) => void = () => undefined
    api.getAiAssistantUsageSession.mockReturnValueOnce(
      new Promise((_, reject) => {
        rejectStaleDetail = reject
      }),
    )
    sessionButton.click()
    await nextTick()
    let resolveRange: (value: { list: Array<typeof firstSession>; total: number; limit: number; offset: number }) => void = () => undefined
    api.getAiAssistantUsageSessions.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRange = resolve
      }),
    )
    const apply = Array.from(host.querySelectorAll('button')).find((button) => button.textContent === '应用')!
    apply.click()
    await nextTick()
    inputs[0].value = '2026-07-02'
    inputs[0].dispatchEvent(new Event('input', { bubbles: true }))
    resolveRange({ list: [firstSession], total: 1, limit: 50, offset: 0 })
    await flushUi()
    expect(api.getAiAssistantUsageDimensions).toHaveBeenLastCalledWith({
      from: '2026-07-01',
      to: '2026-07-11',
      timezone: expect.any(String),
    })
    rejectStaleDetail(new Error('stale detail failed'))
    await flushUi()
    expect(host.querySelector('[data-testid="ai-assistant-usage-detail-error"]')).toBeNull()
    const firstSessionButton = Array.from(host.querySelectorAll('.session-row')).find((button) =>
      button.textContent?.includes('First'),
    ) as HTMLButtonElement
    firstSessionButton.click()
    await flushUi()
    expect(api.getAiAssistantUsageSession).toHaveBeenLastCalledWith(
      1,
      { from: '2026-07-01', to: '2026-07-11', timezone: expect.any(String) },
      { limit: 100, offset: 0 },
    )
    unmount()
  })

  it('renders the empty state from real resolved API behavior', async () => {
    const empty = totals(0, '0.0000000000', 'complete')
    api.getAiAssistantUsageSummary.mockResolvedValue({ today: empty, yesterday: empty, rolling30Days: empty, cumulative: empty })
    api.getAiAssistantUsageDaily.mockResolvedValue({ list: [], total: 0 })
    api.getAiAssistantUsageSessions.mockResolvedValue({ list: [], total: 0, limit: 50, offset: 0 })
    api.getAiAssistantUsageDimensions.mockResolvedValue({
      providers: [], models: [], tokenTypes: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, reasoning: 0, total: 0 },
    })
    const { host, unmount } = mountDashboard()
    await flushUi()
    expect(host.querySelector('[data-testid="ai-assistant-usage-empty"]')).not.toBeNull()
    unmount()
  })

  it('recovers initial errors and keeps detail errors inline with editable range controls', async () => {
    api.getAiAssistantUsageSummary.mockRejectedValueOnce(new Error('summary failed')).mockResolvedValue(summary)
    const { host, unmount } = mountDashboard()
    await flushUi()
    expect(host.querySelector('[data-testid="ai-assistant-usage-error"]')?.textContent).toContain('summary failed')
    ;(host.querySelector('[data-testid="ai-assistant-usage-error"] button') as HTMLButtonElement).click()
    await flushUi()
    expect(host.querySelector('[data-testid="ai-assistant-usage-summary"]')).not.toBeNull()

    const inputs = host.querySelectorAll<HTMLInputElement>('input[type="date"]')
    inputs[0].value = '2026-07-12'
    inputs[0].dispatchEvent(new Event('input', { bubbles: true }))
    inputs[1].value = '2026-07-11'
    inputs[1].dispatchEvent(new Event('input', { bubbles: true }))
    const apply = Array.from(host.querySelectorAll('button')).find((button) => button.textContent === '应用')!
    apply.click()
    await flushUi()
    expect(host.querySelector('[data-testid="ai-assistant-usage-detail-error"]')?.textContent).toContain('开始日期')
    expect(host.querySelector('[data-testid="ai-assistant-usage-summary"]')).not.toBeNull()
    expect(host.querySelector('[data-testid="ai-assistant-usage-range"]')).not.toBeNull()
    unmount()
  })
})
