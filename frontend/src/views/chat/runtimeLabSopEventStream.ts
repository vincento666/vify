import type { RuntimeLabMessagePayload } from '@/api/runtimeLab'
import { buildHostHeaders, resolveApiUrl } from '@/host/request'

export interface RuntimeLabSopStreamFrame {
  type: 'delta' | 'done' | 'error'
  source?: 'runtime_lab' | 'runtime_v2' | 'provider' | string
  sessionId?: number
  runId?: number
  sequence?: number
  delta?: string
  payload?: Record<string, unknown>
  event?: {
    type?: string
    nodeKey?: string | null
    payload?: Record<string, unknown>
  }
  result?: Record<string, unknown>
  error?: string
}

export interface RuntimeLabSopMessageStreamOptions {
  afterSequence?: number
  reconnectDelayMs?: number
  maxReconnects?: number
  onFrame: (frame: RuntimeLabSopStreamFrame) => void
}

export interface RuntimeLabSopMessageStream {
  close: () => void
  lastSequence: () => number
  hasReceivedFrame: () => boolean
  done: Promise<'done' | 'error' | 'closed'>
}

export function openRuntimeLabSopMessageStream(
  sessionId: number,
  payload: RuntimeLabMessagePayload,
  options: RuntimeLabSopMessageStreamOptions,
): RuntimeLabSopMessageStream {
  let lastSequence = options.afterSequence ?? 0
  let receivedFrame = false
  let closed = false
  let controller: AbortController | null = null
  const reconnectDelayMs = Math.max(0, options.reconnectDelayMs ?? 750)
  const maxReconnects = Math.max(0, options.maxReconnects ?? 3)

  const done = consumeRuntimeLabSopMessageStream(
    sessionId,
    payload,
    {
      reconnectDelayMs,
      maxReconnects,
      getLastSequence: () => lastSequence,
      isClosed: () => closed,
      createController: () => {
        controller = new AbortController()
        return controller
      },
      onFrame: (frame) => {
        receivedFrame = true
        lastSequence = Math.max(lastSequence, finiteSequence(frame.sequence))
        options.onFrame(frame)
      },
    },
  )

  return {
    close: () => {
      closed = true
      controller?.abort()
    },
    lastSequence: () => lastSequence,
    hasReceivedFrame: () => receivedFrame,
    done,
  }
}

interface ConsumeOptions {
  reconnectDelayMs: number
  maxReconnects: number
  getLastSequence: () => number
  isClosed: () => boolean
  createController: () => AbortController
  onFrame: (frame: RuntimeLabSopStreamFrame) => void
}

async function consumeRuntimeLabSopMessageStream(
  sessionId: number,
  payload: RuntimeLabMessagePayload,
  options: ConsumeOptions,
): Promise<'done' | 'error' | 'closed'> {
  let reconnects = 0
  while (!options.isClosed()) {
    try {
      const terminal = await consumeOneRuntimeLabSopMessageStream(
        streamUrl(sessionId, options.getLastSequence()),
        payload,
        options.createController().signal,
        options.onFrame,
      )
      if (terminal) return terminal
    } catch (error) {
      if (options.isClosed() || isAbortError(error)) return 'closed'
      if (reconnects >= options.maxReconnects) throw toStreamError(error)
    }
    if (options.isClosed()) return 'closed'
    if (reconnects >= options.maxReconnects) {
      throw new Error('RuntimeLab SOP stream closed before a terminal frame')
    }
    reconnects += 1
    await delay(options.reconnectDelayMs)
  }
  return 'closed'
}

async function consumeOneRuntimeLabSopMessageStream(
  url: string,
  payload: RuntimeLabMessagePayload,
  signal: AbortSignal,
  onFrame: (frame: RuntimeLabSopStreamFrame) => void,
): Promise<'done' | 'error' | null> {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      ...buildHostHeaders(),
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
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
    const consumed = consumeBufferedFrames(buffer, onFrame)
    buffer = consumed.rest
    if (consumed.terminal) return consumed.terminal
  }
  buffer += decoder.decode()
  return consumeBufferedFrames(`${buffer}\n\n`, onFrame).terminal
}

function consumeBufferedFrames(
  buffer: string,
  onFrame: (frame: RuntimeLabSopStreamFrame) => void,
): { rest: string; terminal: 'done' | 'error' | null } {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const frames = normalized.split('\n\n')
  const rest = frames.pop() ?? ''
  for (const raw of frames) {
    const frame = parseRuntimeLabSopFrame(raw)
    if (!frame) continue
    onFrame(frame)
    if (frame.type === 'done' || frame.type === 'error') return { rest, terminal: frame.type }
  }
  return { rest, terminal: null }
}

function parseRuntimeLabSopFrame(raw: string): RuntimeLabSopStreamFrame | null {
  const data: string[] = []
  for (const line of raw.split('\n')) {
    if (!line || line.startsWith(':') || !line.startsWith('data:')) continue
    data.push(line.slice('data:'.length).trimStart())
  }
  if (data.length === 0) return null
  const parsed = JSON.parse(data.join('\n')) as RuntimeLabSopStreamFrame
  if (!['delta', 'done', 'error'].includes(parsed.type)) return null
  return parsed
}

function streamUrl(sessionId: number, afterSequence: number) {
  return resolveApiUrl(`/v1/runtime-lab/sessions/${sessionId}/messages:stream?afterSequence=${afterSequence}`)
}

function finiteSequence(value: unknown): number {
  const sequence = Number(value)
  return Number.isFinite(sequence) ? sequence : 0
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === 'AbortError'
}

function toStreamError(error: unknown): Error {
  if (error instanceof Error) return new Error(`RuntimeLab SOP stream failed: ${error.message}`)
  return new Error('RuntimeLab SOP stream failed')
}
