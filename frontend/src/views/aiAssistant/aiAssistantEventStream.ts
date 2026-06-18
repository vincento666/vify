import type { AiAssistantEvent } from '@/api/aiAssistant'
import { buildHostHeaders, resolveApiUrl } from '@/host/request'

export interface AiAssistantEventStreamOptions {
  afterSequence?: number
  onEvent: (event: AiAssistantEvent) => void
  onError?: (error: Error) => void
}

export interface AiAssistantEventStream {
  close: () => void
  lastSequence: () => number
}

export function openAiAssistantEventStream(
  runId: number,
  options: AiAssistantEventStreamOptions,
): AiAssistantEventStream {
  let lastSequence = options.afterSequence ?? 0
  let closed = false
  const controller = new AbortController()
  const url = resolveApiUrl(`/v1/ai-assistant/runs/${runId}/events/stream?afterSequence=${lastSequence}`)
  void consumeAiAssistantEventStream(
    url,
    controller.signal,
    (event) => {
      lastSequence = Math.max(lastSequence, Number(event.sequence || 0))
      options.onEvent(event)
    },
    (error) => {
      if (!closed) options.onError?.(toStreamError(error))
    },
  )

  return {
    close: () => {
      closed = true
      controller.abort()
    },
    lastSequence: () => lastSequence,
  }
}

async function consumeAiAssistantEventStream(
  url: string,
  signal: AbortSignal,
  onEvent: (event: AiAssistantEvent) => void,
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

function consumeBufferedFrames(buffer: string, onEvent: (event: AiAssistantEvent) => void): string {
  const normalized = buffer.replace(/\r\n/g, '\n')
  const frames = normalized.split('\n\n')
  const rest = frames.pop() ?? ''
  for (const frame of frames) {
    const event = parseAiAssistantEventFrame(frame)
    if (event) onEvent(event)
  }
  return rest
}

function parseAiAssistantEventFrame(frame: string): AiAssistantEvent | null {
  let eventType = 'message'
  const data: string[] = []
  for (const line of frame.split('\n')) {
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) eventType = line.slice('event:'.length).trim()
    if (line.startsWith('data:')) data.push(line.slice('data:'.length).trimStart())
  }
  if (eventType !== 'ai_assistant_event' || data.length === 0) return null
  return JSON.parse(data.join('\n')) as AiAssistantEvent
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

function toStreamError(error: unknown): Error {
  if (error instanceof Error) return new Error(`AI 助手事件流失败：${error.message}`)
  return new Error('AI 助手事件流失败')
}
