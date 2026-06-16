import type { CustomerAssistantEvent } from '@/api/customerAssistant'
import { resolveApiUrl } from '@/host/request'

export interface CustomerAssistantEventStreamOptions {
  afterSequence?: number
  onEvent: (event: CustomerAssistantEvent) => void
  onError?: (error: Error) => void
}

export interface CustomerAssistantEventStream {
  close: () => void
  lastSequence: () => number
}

export function openCustomerAssistantEventStream(
  sessionId: number,
  options: CustomerAssistantEventStreamOptions,
): CustomerAssistantEventStream {
  let lastSequence = options.afterSequence ?? 0
  const url = resolveApiUrl(
    `/v1/customer-assistant/sessions/${sessionId}/events/stream?afterSequence=${lastSequence}`,
  )
  const source = new EventSource(url)

  source.addEventListener('customer_assistant_event', (message) => {
    try {
      const event = JSON.parse(message.data) as CustomerAssistantEvent
      lastSequence = Math.max(lastSequence, Number(event.sequence || 0))
      options.onEvent(event)
    } catch (error) {
      options.onError?.(toStreamError(error))
    }
  })
  source.onerror = () => {
    options.onError?.(new Error('Customer assistant event stream failed'))
  }

  return {
    close: () => source.close(),
    lastSequence: () => lastSequence,
  }
}

function toStreamError(error: unknown): Error {
  if (error instanceof Error) {
    return new Error(`Customer assistant event stream failed: ${error.message}`)
  }
  return new Error('Customer assistant event stream failed')
}
