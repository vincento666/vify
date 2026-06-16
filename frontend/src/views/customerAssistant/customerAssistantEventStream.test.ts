import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { CustomerAssistantEvent } from '@/api/customerAssistant'

class FakeEventSource {
  static instances: FakeEventSource[] = []
  listeners = new Map<string, Array<(event: MessageEvent) => void>>()
  onerror: ((event: Event) => void) | null = null
  closed = false

  constructor(public url: string) {
    FakeEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener])
  }

  close() {
    this.closed = true
  }

  emit(type: string, data: CustomerAssistantEvent) {
    for (const listener of this.listeners.get(type) ?? []) {
      listener({ data: JSON.stringify(data) } as MessageEvent)
    }
  }

  fail() {
    this.onerror?.(new Event('error'))
  }
}

describe('customer-assistant SSE client', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('opens a resumable stream, parses events, tracks sequence, and closes', async () => {
    const received: CustomerAssistantEvent[] = []
    const errors: Error[] = []
    const { openCustomerAssistantEventStream } = await import('./customerAssistantEventStream')

    const stream = openCustomerAssistantEventStream(7, {
      afterSequence: 3,
      onEvent: (event) => received.push(event),
      onError: (error) => errors.push(error),
    })
    const source = FakeEventSource.instances[0]

    source.emit('customer_assistant_event', {
      id: 11,
      sessionId: 7,
      runId: 4,
      sequence: 4,
      type: 'run_started',
      payload: { actor: 'customer' },
    })
    source.fail()
    stream.close()

    expect(source.url).toBe('/api/v1/customer-assistant/sessions/7/events/stream?afterSequence=3')
    expect(received).toHaveLength(1)
    expect(received[0].sequence).toBe(4)
    expect(stream.lastSequence()).toBe(4)
    expect(errors[0].message).toContain('Customer assistant event stream failed')
    expect(source.closed).toBe(true)
  })
})
