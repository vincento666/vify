import { describe, expect, it } from 'vitest'

import type { AiAssistantEvent } from '@/api/aiAssistant'
import { buildAiAssistantTimeline } from './aiAssistantTimeline'

describe('ai assistant execution timeline', () => {
  it('maps durable run events into visible Codex-style execution cards', () => {
    const events: AiAssistantEvent[] = [
      {
        id: 1,
        sessionId: 1,
        runId: 2,
        sequence: 1,
        type: 'run.started',
        level: 'info',
        status: 'COMPLETED',
        visibleTitle: 'Run started',
        visibleSummary: 'The assistant run started.',
        payload: {},
        createdAt: '2026-06-17T10:00:00',
      },
      {
        id: 2,
        sessionId: 1,
        runId: 2,
        sequence: 2,
        type: 'tool.call_output',
        level: 'info',
        status: 'COMPLETED',
        visibleTitle: 'Tool output',
        visibleSummary: 'long output',
        payload: { output: { echo: 'hello' } },
        createdAt: '2026-06-17T10:00:01',
      },
      {
        id: 3,
        sessionId: 1,
        runId: 2,
        sequence: 3,
        type: 'approval.required',
        level: 'info',
        status: 'WAITING',
        visibleTitle: 'Approval required',
        visibleSummary: 'update_customer_profile requires approval.',
        payload: { approvalId: 9, riskLevel: 'BUSINESS_WRITE' },
        createdAt: '2026-06-17T10:00:02',
      },
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.kind)).toEqual(['phase', 'tool-output', 'approval'])
    expect(timeline[0].tone).toBe('running')
    expect(timeline[1].payloadPreview).toContain('hello')
    expect(timeline[2].approvalId).toBe(9)
  })
})
