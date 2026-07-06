import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AiAssistantEvent } from '@/api/aiAssistant'

vi.mock('@/host/request', () => ({
  buildHostHeaders: () => ({ 'X-Hify-Test': '1' }),
  resolveApiUrl: (path: string) => `http://hify.test${path}`,
}))

describe('ai assistant event stream', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('reconnects with the latest sequence after a dropped SSE response', async () => {
    vi.useFakeTimers()
    const first = aiAssistantEvent(5, 'text.delta', { delta: '你' })
    const second = aiAssistantEvent(6, 'text.delta', { delta: '好' })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(closedSseResponse(sseFrame(first)))
      .mockResolvedValueOnce(closedSseResponse(sseFrame(second)))
    vi.stubGlobal('fetch', fetchMock)
    const { openAiAssistantEventStream } = await import('./aiAssistantEventStream')
    const received: AiAssistantEvent[] = []

    const stream = openAiAssistantEventStream(42, {
      afterSequence: 4,
      reconnectDelayMs: 10,
      onEvent: (event) => received.push(event),
    })

    await vi.waitFor(() => expect(received).toHaveLength(1))
    await vi.advanceTimersByTimeAsync(10)
    await vi.waitFor(() => expect(received).toHaveLength(2))
    stream.close()
    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2)

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      'http://hify.test/v1/ai-assistant/runs/42/events/stream?afterSequence=4',
      expect.objectContaining({ headers: expect.objectContaining({ Accept: 'text/event-stream' }) }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      'http://hify.test/v1/ai-assistant/runs/42/events/stream?afterSequence=5',
      expect.any(Object),
    )
    expect(stream.lastSequence()).toBe(6)
    expect(received.map((event) => event.payload.delta)).toEqual(['你', '好'])
  })
})

function aiAssistantEvent(sequence: number, type: string, payload: Record<string, unknown>): AiAssistantEvent {
  return {
    id: sequence,
    sessionId: 1,
    runId: 42,
    sequence,
    type,
    level: 'info',
    status: 'COMPLETED',
    visibleTitle: '实时输出',
    visibleSummary: String(payload.delta ?? ''),
    payload,
    createdAt: '2026-07-01T00:00:00',
  }
}

function sseFrame(event: AiAssistantEvent) {
  return `event: ai_assistant_event\ndata: ${JSON.stringify(event)}\n\n`
}

function closedSseResponse(frame: string) {
  const encoder = new TextEncoder()
  return {
    ok: true,
    body: new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(frame))
        controller.close()
      },
    }),
  } as Response
}
