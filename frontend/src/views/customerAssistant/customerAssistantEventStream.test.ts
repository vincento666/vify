import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { CustomerAssistantEvent } from '@/api/customerAssistant'

function sseChunk(event: CustomerAssistantEvent) {
  return new TextEncoder().encode(
    `id: ${event.sequence}\nevent: customer_assistant_event\ndata: ${JSON.stringify(event)}\n\n`,
  )
}

describe('customer-assistant SSE client', () => {
  beforeEach(() => {
    globalThis.__HIFY_HOST__ = {
      apiBaseUrl: '/api',
      actorId: 'operator-stream',
      tenantId: 'tenant-stream',
      permissions: ['customer_assistant:read'],
      requestId: 'req-stream',
      source: 'embedded-demo-shell',
    }
  })

  afterEach(() => {
    delete globalThis.__HIFY_HOST__
    vi.unstubAllGlobals()
  })

  it('opens a resumable fetch stream with host headers, parses events, tracks sequence, and closes', async () => {
    const received: CustomerAssistantEvent[] = []
    const errors: Error[] = []
    const fetchSpy = vi.fn(async (_url: string, _init?: RequestInit) => new Response(
      new ReadableStream({
        start(controller) {
          controller.enqueue(sseChunk({
            id: 11,
            sessionId: 7,
            runId: 4,
            sequence: 4,
            type: 'run_started',
            payload: { actor: 'customer' },
          }))
          controller.close()
        },
      }),
      { status: 200, headers: { 'Content-Type': 'text/event-stream' } },
    ))
    vi.stubGlobal('fetch', fetchSpy)
    const { openCustomerAssistantEventStream } = await import('./customerAssistantEventStream')

    const stream = openCustomerAssistantEventStream(7, {
      afterSequence: 3,
      onEvent: (event) => received.push(event),
      onError: (error) => errors.push(error),
    })
    await vi.waitUntil(() => received.length === 1)
    stream.close()

    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/customer-assistant/sessions/7/events/stream?afterSequence=3')
    expect(init.headers).toMatchObject({
      Accept: 'text/event-stream',
      'X-Hify-Actor-Id': 'operator-stream',
      'X-Hify-Tenant-Id': 'tenant-stream',
      'X-Hify-Permissions': 'customer_assistant:read',
      'X-Request-Id': 'req-stream',
    })
    expect(received).toHaveLength(1)
    expect(received[0].sequence).toBe(4)
    expect(stream.lastSequence()).toBe(4)
    expect(errors).toHaveLength(0)
  })

  it('reports fetch stream failures', async () => {
    const errors: Error[] = []
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 403 })))
    const { openCustomerAssistantEventStream } = await import('./customerAssistantEventStream')

    openCustomerAssistantEventStream(7, {
      onEvent: () => {},
      onError: (error) => errors.push(error),
    })
    await vi.waitUntil(() => errors.length === 1)

    expect(errors[0].message).toContain('Customer assistant event stream failed')
  })
})
