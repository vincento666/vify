import { buildHostHeaders, resolveApiUrl } from '@/host/request'

export interface RuntimeOpsRealtimeEvent extends Record<string, any> {
  sequence?: number
  type?: string
}

export interface RuntimeOpsEventStreamStatus {
  state: 'connecting' | 'open' | 'reconnecting' | 'closed'
  lastSequence: number
  reconnects: number
  latestType: string
}

export interface RuntimeOpsEventStreamOptions {
  afterSequence?: number
  reconnectDelayMs?: number
  onEvent: (event: RuntimeOpsRealtimeEvent) => void
  onStatus?: (status: RuntimeOpsEventStreamStatus) => void
  onError?: (error: Error) => void
}

export interface RuntimeOpsEventStream {
  close: () => void
  lastSequence: () => number
  reconnects: () => number
}

export function openRuntimeOpsEventStream(runId: number, options: RuntimeOpsEventStreamOptions): RuntimeOpsEventStream {
  let lastSequence = options.afterSequence ?? 0
  let reconnects = 0
  let latestType = '-'
  let closed = false
  let controller: AbortController | null = null
  const reconnectDelayMs = options.reconnectDelayMs ?? 1000

  const emitStatus = (state: RuntimeOpsEventStreamStatus['state']) => {
    options.onStatus?.({ state, lastSequence, reconnects, latestType })
  }

  const consumeLoop = async () => {
    while (!closed) {
      controller = new AbortController()
      emitStatus(reconnects > 0 ? 'reconnecting' : 'connecting')
      try {
        await consumeRuntimeOpsEventStream(
          streamUrl(runId, lastSequence),
          controller.signal,
          (event) => {
            lastSequence = Math.max(lastSequence, Number(event.sequence || 0))
            latestType = String(event.type || 'runtime_event')
            options.onEvent(event)
            emitStatus('open')
          },
        )
      } catch (error) {
        if (isAbortError(error)) return
        options.onError?.(toStreamError(error))
      }
      if (closed) break
      await sleep(reconnectDelayMs)
      if (!closed) reconnects += 1
    }
  }

  void consumeLoop()

  return {
    close: () => {
      closed = true
      controller?.abort()
      emitStatus('closed')
    },
    lastSequence: () => lastSequence,
    reconnects: () => reconnects,
  }
}

async function consumeRuntimeOpsEventStream(
  url: string,
  signal: AbortSignal,
  onEvent: (event: RuntimeOpsRealtimeEvent) => void,
) {
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
}

function consumeBufferedFrames(buffer: string, onEvent: (event: RuntimeOpsRealtimeEvent) => void): string {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const frames = normalized.split('\n\n')
  const rest = frames.pop() ?? ''
  for (const frame of frames) {
    const event = parseRuntimeOpsEventFrame(frame)
    if (event) onEvent(event)
  }
  return rest
}

function parseRuntimeOpsEventFrame(frame: string): RuntimeOpsRealtimeEvent | null {
  const data: string[] = []
  for (const line of frame.split('\n')) {
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('data:')) data.push(line.slice('data:'.length).trimStart())
  }
  if (data.length === 0) return null
  return JSON.parse(data.join('\n')) as RuntimeOpsRealtimeEvent
}

function streamUrl(runId: number, afterSequence: number) {
  return resolveApiUrl(`/v1/runtime-runs/${runId}/events/stream?afterSequence=${afterSequence}`)
}

function sleep(ms: number) {
  return new Promise((resolve) => globalThis.setTimeout(resolve, ms))
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

function toStreamError(error: unknown): Error {
  if (error instanceof Error) return new Error(`Runtime Ops event stream failed: ${error.message}`)
  return new Error('Runtime Ops event stream failed')
}
