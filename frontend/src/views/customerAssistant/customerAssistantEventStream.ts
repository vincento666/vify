import type { CustomerAssistantEvent } from '@/api/customerAssistant'
import { buildHostHeaders, resolveApiUrl } from '@/host/request'

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
  let closed = false
  const controller = new AbortController()
  const url = resolveApiUrl(
    `/v1/customer-assistant/sessions/${sessionId}/events/stream?afterSequence=${lastSequence}`,
  )
  void consumeCustomerAssistantEventStream(url, controller.signal, (event) => {
    lastSequence = Math.max(lastSequence, Number(event.sequence || 0))
    options.onEvent(event)
  }, (error) => {
    if (!closed) options.onError?.(toStreamError(error))
  })

  return {
    close: () => {
      closed = true
      controller.abort()
    },
    lastSequence: () => lastSequence,
  }
}

async function consumeCustomerAssistantEventStream(
  url: string,
  signal: AbortSignal,
  onEvent: (event: CustomerAssistantEvent) => void,
  onError: (error: unknown) => void,
) {
  try {
    const response = await fetch(url, {
      headers: {
        ...buildHostHeaders(),
        Accept: 'text/event-stream',
      },
      signal,
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    if (!response.body) throw new Error('missing stream body')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      buffer = consumeBufferedFrames(buffer, onEvent)
    }
    buffer += decoder.decode()
    consumeBufferedFrames(`${buffer}\n\n`, onEvent)
  } catch (error) {
    if (isAbortError(error)) return
    onError(error)
  }
}

function consumeBufferedFrames(buffer: string, onEvent: (event: CustomerAssistantEvent) => void): string {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const frames = normalized.split('\n\n')
  const rest = frames.pop() ?? ''
  for (const frame of frames) {
    const event = parseCustomerAssistantEventFrame(frame)
    if (event) onEvent(event)
  }
  return rest
}

function parseCustomerAssistantEventFrame(frame: string): CustomerAssistantEvent | null {
  let eventType = 'message'
  const data: string[] = []
  for (const line of frame.split('\n')) {
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) eventType = line.slice('event:'.length).trim()
    if (line.startsWith('data:')) data.push(line.slice('data:'.length).trimStart())
  }
  if (eventType !== 'customer_assistant_event' || data.length === 0) return null
  return JSON.parse(data.join('\n')) as CustomerAssistantEvent
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

function toStreamError(error: unknown): Error {
  if (error instanceof Error) {
    return new Error(`Customer assistant event stream failed: ${error.message}`)
  }
  return new Error('Customer assistant event stream failed')
}
