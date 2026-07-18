import { describe, expect, it } from 'vitest'

import type { AiAssistantEvent } from '@/api/aiAssistant'
import type { RunActivity } from './aiAssistantActivity'
import {
  activityExpansionKey,
  activityProgress,
  activityTimelineItems,
  buildRunActivityFeed,
  isActivityExpanded,
  summarizeSubagentPresence,
  withActivityExpansion,
} from './aiAssistantActivityView'
import { buildAiAssistantTimeline } from './aiAssistantTimeline'

describe('AI Assistant activity shell view model', () => {
  it('uses stable run and activity identity for manual expansion overrides', () => {
    const running = activity({ status: 'running', lastSequence: 4 })
    const completed = activity({ status: 'completed', lastSequence: 8 })
    const waiting = activity({ id: 'approval:7', kind: 'approval', status: 'waiting_approval' })
    const failed = activity({ id: 'tool-call:9', status: 'failed' })

    expect(activityExpansionKey(running)).toBe('run:2/activity:tool-call:4')
    expect(isActivityExpanded(running, {})).toBe(true)
    expect(isActivityExpanded(completed, {})).toBe(false)
    expect(isActivityExpanded(waiting, {})).toBe(true)
    expect(isActivityExpanded(failed, {})).toBe(true)

    const override = withActivityExpansion({}, running, false)
    expect(isActivityExpanded({ ...running, lastSequence: 99 }, override)).toBe(false)
    expect(isActivityExpanded(completed, withActivityExpansion({}, completed, true))).toBe(true)
  })

  it('summarizes only projected durable child execution lifecycles', () => {
    const presence = summarizeSubagentPresence([
      activity({
        id: 'subagent:customer-run-1',
        kind: 'subagent',
        status: 'running',
        executionId: 'customer-run-1',
        title: '客户资料核验',
      }),
      activity({
        id: 'subagent:customer-run-2',
        kind: 'subagent',
        status: 'completed',
        executionId: 'customer-run-2',
        title: '订单检查',
      }),
      activity({ id: 'tool-call:8', kind: 'tool', status: 'running' }),
    ])

    expect(presence.runningCount).toBe(1)
    expect(presence.activeCount).toBe(1)
    expect(presence.completedCount).toBe(1)
    expect(presence.items.map((item) => item.executionId)).toEqual(['customer-run-1', 'customer-run-2'])
  })

  it('places streaming model output and stable activities in one ordered feed', () => {
    const events = [
      event({
        id: 1,
        sequence: 1,
        type: 'orchestration.phase_started',
        status: 'RUNNING',
        visibleTitle: '理解任务',
        correlationIds: { activityId: 'phase:understand' },
      }),
      event({
        id: 2,
        sequence: 2,
        type: 'text.delta',
        status: 'RUNNING',
        visibleSummary: '我先检查',
        payload: { delta: '我先检查', streaming: true },
      }),
      event({
        id: 3,
        sequence: 3,
        type: 'tool.call_started',
        status: 'RUNNING',
        visibleTitle: '读取工作区文件',
        payload: { toolName: 'read_workspace_file', input: { path: 'AGENTS.md' } },
        correlationIds: { activityId: 'tool-call:7', parentActivityId: 'phase:understand' },
      }),
    ]

    expect(buildRunActivityFeed(events).map((item) => [item.kind, item.id])).toEqual([
      ['activity', 'activity:phase:understand'],
      ['model-output', 'model-output:2-2-2-text.delta'],
      ['activity', 'activity:tool-call:7'],
    ])
  })

  it('selects raw audit details by stable event identity', () => {
    const events = [
      event({
        id: 11,
        sequence: 11,
        type: 'tool.call_started',
        status: 'RUNNING',
        payload: { toolName: 'read_workspace_file', input: { path: 'AGENTS.md' } },
        correlationIds: { activityId: 'tool-call:11' },
      }),
      event({
        id: 13,
        sequence: 12,
        type: 'approval.approved',
        status: 'COMPLETED',
        visibleTitle: '审批通过',
        payload: { approvalId: 8 },
        correlationIds: { activityId: 'approval:8' },
      }),
      event({
        id: 12,
        sequence: 13,
        type: 'tool.call_completed',
        status: 'COMPLETED',
        payload: { toolName: 'read_workspace_file', output: { content: '# Guide' }, status: 'COMPLETED' },
        correlationIds: { activityId: 'tool-call:11' },
      }),
    ]
    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.find((item) => item.kind === 'file')?.eventIds).toEqual([11, 12])
    expect(activityTimelineItems(activity({ eventIds: [11, 12], firstSequence: 11, lastSequence: 13 }), timeline))
      .toEqual([expect.objectContaining({ kind: 'file', eventId: 12 })])
  })

  it('keeps a waiting approval in its activity for inline operator action', () => {
    const required = event({
      id: 21,
      sequence: 21,
      type: 'approval.required',
      status: 'WAITING',
      visibleTitle: '需要审批',
      visibleSummary: '写入前需要操作员确认。',
      payload: { approvalId: 8, toolName: 'update_customer_profile' },
      correlationIds: { activityId: 'approval:8' },
    })
    const timeline = buildAiAssistantTimeline([required])

    expect(activityTimelineItems(
      activity({
        id: 'approval:8',
        kind: 'approval',
        status: 'waiting_approval',
        eventIds: [21],
        firstSequence: 21,
        lastSequence: 21,
      }),
      timeline,
    )).toEqual([
      expect.objectContaining({
        kind: 'approval',
        eventId: 21,
        approvalId: 8,
        tone: 'waiting',
        title: '需要审批',
      }),
    ])
  })

  it('shows progress only when a durable plan step matches stable activity identity', () => {
    const step = activity({
      id: 'run:2:step:inspect',
      kind: 'step',
      title: '检查配置',
    })
    const steps = [{ id: 'inspect' }, { id: 'report' }]

    expect(activityProgress(step, steps)).toEqual({ current: 1, total: 2 })
    expect(activityProgress(activity({ kind: 'tool' }), steps)).toBeUndefined()
    expect(activityProgress({ ...step, id: 'run:2:step:missing' }, steps)).toBeUndefined()
  })
})

function activity(overrides: Partial<RunActivity> = {}): RunActivity {
  return {
    id: 'tool-call:4',
    runId: 2,
    kind: 'tool',
    status: 'running',
    title: '读取工作区文件',
    summary: '正在读取 AGENTS.md',
    startedAt: '2026-07-18T10:00:00Z',
    firstSequence: 4,
    lastSequence: 4,
    eventIds: [4],
    detailRef: {
      runId: 2,
      firstSequence: 4,
      lastSequence: 4,
      eventIds: [4],
    },
    ...overrides,
  }
}

function event(
  overrides: Partial<AiAssistantEvent> & Pick<AiAssistantEvent, 'id' | 'sequence' | 'type' | 'status'>,
): AiAssistantEvent {
  return {
    sessionId: 1,
    runId: 2,
    level: 'info',
    visibleTitle: overrides.type,
    visibleSummary: overrides.type,
    payload: {},
    createdAt: '2026-07-18T10:00:00Z',
    ...overrides,
  }
}
