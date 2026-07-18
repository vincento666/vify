import { describe, expect, it } from 'vitest'

import type { AiAssistantEvent } from '@/api/aiAssistant'
import { projectRunActivities } from './aiAssistantActivity'

describe('ai assistant run activity projection', () => {
  it('keeps activity identity stable while a tool call receives later events', () => {
    const started = activityEvent({
      id: 11,
      sequence: 11,
      type: 'tool.call_started',
      status: 'RUNNING',
      toolCallId: 41,
      payload: { toolName: 'read_workspace_file', input: { path: 'AGENTS.md' } },
      correlationIds: { activityId: 'tool-call:41' },
    })
    const completed = activityEvent({
      id: 12,
      sequence: 12,
      type: 'tool.call_completed',
      status: 'COMPLETED',
      toolCallId: 41,
      payload: { toolName: 'read_workspace_file', status: 'COMPLETED' },
      correlationIds: { activityId: 'tool-call:41' },
    })

    const running = projectRunActivities([started])
    const finished = projectRunActivities([started, completed])

    expect(running).toHaveLength(1)
    expect(finished).toHaveLength(1)
    expect(running[0].id).toBe('tool-call:41')
    expect(finished[0].id).toBe(running[0].id)
    expect(finished[0]).toMatchObject({
      kind: 'tool',
      status: 'completed',
      firstSequence: 11,
      lastSequence: 12,
      eventIds: [11, 12],
    })
  })

  it('deduplicates replayed events and never regresses terminal state on reordered input', () => {
    const started = activityEvent({
      id: 21,
      sequence: 21,
      type: 'tool.call_started',
      status: 'RUNNING',
      toolCallId: 51,
      payload: { toolName: 'search_knowledge_base' },
      correlationIds: { activityId: 'tool-call:51' },
    })
    const completed = activityEvent({
      id: 22,
      sequence: 22,
      type: 'tool.call_completed',
      status: 'COMPLETED',
      toolCallId: 51,
      payload: { toolName: 'search_knowledge_base', status: 'COMPLETED' },
      correlationIds: { activityId: 'tool-call:51' },
    })

    const activities = projectRunActivities([completed, started, { ...completed }])

    expect(activities).toHaveLength(1)
    expect(activities[0].status).toBe('completed')
    expect(activities[0].eventIds).toEqual([21, 22])
  })

  it('does not present a link-only bridge result as a running subagent', () => {
    const linked = activityEvent({
      id: 31,
      sequence: 31,
      type: 'subagent.linked',
      status: 'COMPLETED',
      payload: {
        executionId: 'customer-assistant-run-34',
        status: 'linked',
        eventStreamRef: '/api/v1/customer-assistant/sessions/12/events/stream',
        resultRef: '/api/v1/customer-assistant/runs/34',
      },
      correlationIds: { activityId: 'subagent:customer-assistant-run-34' },
    })
    const started = activityEvent({
      id: 32,
      sequence: 32,
      type: 'subagent.execution_started',
      status: 'RUNNING',
      payload: {
        executionId: 'customer-assistant-run-34',
        agentType: 'customer_assistant',
        status: 'running',
        statusRef: '/api/v1/customer-assistant/runs/34',
        eventStreamRef: '/api/v1/customer-assistant/sessions/12/events/stream',
        resultRef: '/api/v1/customer-assistant/runs/34',
      },
      correlationIds: { activityId: 'subagent:customer-assistant-run-34' },
    })

    expect(projectRunActivities([linked])).toEqual([])
    expect(projectRunActivities([linked, started])).toEqual([
      expect.objectContaining({
        id: 'subagent:customer-assistant-run-34',
        kind: 'subagent',
        status: 'running',
        executionId: 'customer-assistant-run-34',
      }),
    ])
  })

  it('keeps legacy events without stable correlation out of the activity state machine', () => {
    const legacy = activityEvent({
      id: 41,
      sequence: 41,
      type: 'tool.call_started',
      status: 'RUNNING',
      payload: { toolName: 'read_workspace_file' },
    })

    expect(projectRunActivities([legacy])).toEqual([])
  })
})

function activityEvent(
  overrides: Partial<AiAssistantEvent> & Pick<AiAssistantEvent, 'id' | 'sequence' | 'type' | 'status' | 'payload'>,
): AiAssistantEvent {
  return {
    sessionId: 1,
    runId: 2,
    level: 'info',
    visibleTitle: overrides.type,
    visibleSummary: overrides.type,
    createdAt: '2026-07-18T10:00:00',
    ...overrides,
  }
}
