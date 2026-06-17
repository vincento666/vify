// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import {
  applyCustomerAssistantDraftLocally,
  createCustomerAssistantDraftState,
  formatCustomerAssistantEvents,
  formatCustomerAssistantTurnStatus,
} from './customerAssistantViewModel'
import { mockCustomerAssistantEvents, mockCustomerAssistantTurnResult } from './customerAssistantFixtures'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

describe('customer assistant interaction polish', () => {
  it('copies/applies customer draft locally without marking it outbound', () => {
    const draft = createCustomerAssistantDraftState(mockCustomerAssistantTurnResult.customerReplyDraft)
    const applied = applyCustomerAssistantDraftLocally(draft)

    expect(draft).toMatchObject({
      text: mockCustomerAssistantTurnResult.customerReplyDraft,
      applied: false,
      outbound: false,
      copyLabel: '复制客户回复草稿',
      applyLabel: '本地应用客户回复草稿',
    })
    expect(applied).toMatchObject({
      applied: true,
      outbound: false,
    })
  })

  it('formats loading, failed, replayed, and ready turn states', () => {
    expect(formatCustomerAssistantTurnStatus({ loading: true })).toMatchObject({
      kind: 'loading',
      label: '正在请求客服助手',
    })
    expect(formatCustomerAssistantTurnStatus({ error: 'API down' })).toMatchObject({
      kind: 'failed',
      label: '调用失败',
      detail: 'API down',
    })
    expect(formatCustomerAssistantTurnStatus({ replayed: true })).toMatchObject({
      kind: 'replayed',
      label: '已复用幂等结果',
    })
    expect(formatCustomerAssistantTurnStatus({})).toMatchObject({
      kind: 'ready',
      label: '等待输入',
    })
  })

  it('keeps debug event payloads collapsed by default', () => {
    const rows = formatCustomerAssistantEvents([
      {
        ...mockCustomerAssistantEvents.list[0],
        visibility: 'debug',
      },
    ])

    expect(rows[0]).toMatchObject({
      debug: true,
      defaultCollapsed: true,
    })
  })

  it('renders accessible labels, tooltips, and explicit empty/failed/replayed states', () => {
    const content = readProjectFile('src/views/customerAssistant/CustomerAssistantPanel.vue')

    expect(content).toContain('<a-tooltip')
    expect(content).toContain('aria-label="复制客户回复草稿"')
    expect(content).toContain('aria-label="本地应用客户回复草稿"')
    expect(content).toContain('aria-label="确认拟议动作"')
    expect(content).toContain('aria-label="拒绝拟议动作"')
    expect(content).toContain('aria-label="确认备注"')
    expect(content).toContain('aria-label="拒绝原因"')
    expect(content).toContain('data-testid="customer-assistant-empty-state"')
    expect(content).toContain('data-testid="customer-assistant-failed-state"')
    expect(content).toContain('data-testid="customer-assistant-replayed-state"')
  })

  it('passes decision note payloads through confirm and reject actions', () => {
    const content = readProjectFile('src/views/customerAssistant/CustomerAssistantPanel.vue')

    expect(content).toContain('confirmCustomerAssistantRuntimeAction(runtimeState.value, actionId, payload)')
    expect(content).toContain('rejectCustomerAssistantRuntimeAction(runtimeState.value, actionId, payload)')
    expect(content).toContain('actionConfirmDecisionPayload(actionId)')
    expect(content).toContain('actionRejectDecisionPayload(actionId)')
    expect(content).toContain('clearActionDecisionDraft(actionId)')
  })

  it('persists action and task-control failures in the workbench failed-state alert', () => {
    const content = readProjectFile('src/views/customerAssistant/CustomerAssistantPanel.vue')

    expect(content).toContain('setRuntimeError(errorMessage)')
    expect(content).toContain("catchCustomerAssistantError(error, '确认动作失败')")
    expect(content).toContain("catchCustomerAssistantError(error, '拒绝动作失败')")
    expect(content).toContain("catchCustomerAssistantError(error, '执行动作失败')")
    expect(content).toContain("catchCustomerAssistantError(error, '生成任务控制失败')")
  })
})
