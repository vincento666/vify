import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { RuntimeOpsEventStream, RuntimeOpsRealtimeEvent } from './runtimeOpsEventStream'

function sseChunk(event: RuntimeOpsRealtimeEvent) {
  return new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`)
}

describe('runtime ops SSE stream client', () => {
  beforeEach(() => {
    globalThis.__HIFY_HOST__ = {
      apiBaseUrl: '/api',
      actorId: 'operator-runtime-ops',
      tenantId: 'tenant-runtime-ops',
      permissions: ['runtime_ops:read'],
      requestId: 'req-runtime-ops',
      source: 'embedded-demo-shell',
    }
  })

  afterEach(() => {
    delete globalThis.__HIFY_HOST__
    vi.unstubAllGlobals()
  })

  it('resumes with afterSequence after a closed fetch stream', async () => {
    const received: RuntimeOpsRealtimeEvent[] = []
    const fetchSpy = vi
      .fn()
      .mockResolvedValueOnce(streamResponse({ sequence: 4, type: 'workflow_node_started' }))
      .mockResolvedValueOnce(streamResponse({ sequence: 5, type: 'workflow_node_completed' }))
    vi.stubGlobal('fetch', fetchSpy)
    const { openRuntimeOpsEventStream } = await import('./runtimeOpsEventStream')

    let stream: RuntimeOpsEventStream
    stream = openRuntimeOpsEventStream(701, {
      afterSequence: 3,
      reconnectDelayMs: 1,
      onEvent: (event) => {
        received.push(event)
        if (received.length === 2) stream.close()
      },
    })
    await vi.waitUntil(() => received.length === 2)

    const [firstUrl, firstInit] = fetchSpy.mock.calls[0] as [string, RequestInit]
    const [secondUrl] = fetchSpy.mock.calls[1] as [string, RequestInit]
    expect(firstUrl).toBe('/api/v1/runtime-runs/701/events/stream?afterSequence=3')
    expect(secondUrl).toBe('/api/v1/runtime-runs/701/events/stream?afterSequence=4')
    expect(firstInit.headers).toMatchObject({
      Accept: 'text/event-stream',
      'X-Hify-Actor-Id': 'operator-runtime-ops',
      'X-Hify-Tenant-Id': 'tenant-runtime-ops',
      'X-Hify-Permissions': 'runtime_ops:read',
      'X-Request-Id': 'req-runtime-ops',
    })
    expect(stream.lastSequence()).toBe(5)
    expect(stream.reconnects()).toBe(1)
  })
})

function streamResponse(event: RuntimeOpsRealtimeEvent) {
  return new Response(
    new ReadableStream({
      start(controller) {
        controller.enqueue(sseChunk(event))
        controller.close()
      },
    }),
    { status: 200, headers: { 'Content-Type': 'text/event-stream' } },
  )
}
