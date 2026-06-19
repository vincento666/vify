export interface ChatflowWelcomeState {
  openingMessage: string
  suggestedQuestions: string[]
}

export interface ChatflowStreamEventLike {
  [key: string]: unknown
  type?: string
  nodeKey?: string
  content?: unknown
  delta?: unknown
  text?: unknown
  message?: unknown
  payload?: Record<string, unknown>
}

export interface ChatflowStreamPreview {
  content: string
  chunks: string[]
  done: boolean
  error: string
  finalContent: string
  streaming: boolean
}

export function buildChatflowWelcomeState(openingMessage: string, suggestedQuestions: string[]): ChatflowWelcomeState {
  return {
    openingMessage: String(openingMessage || '').trim(),
    suggestedQuestions: normalizeSuggestedQuestions(suggestedQuestions),
  }
}

export function buildChatflowStreamPreview(
  events: ChatflowStreamEventLike[] | null | undefined,
  output?: Record<string, unknown> | null,
): ChatflowStreamPreview {
  const chunks: string[] = []
  let done = false
  let finalContent = ''
  let error = ''

  for (const event of events || []) {
    const type = String(event?.type || '')
    if (type === 'message_delta' || type === 'llm_delta') {
      const chunk = streamEventText(event)
      if (chunk) chunks.push(chunk)
      continue
    }
    if (type === 'message_done') {
      done = true
      const content = streamEventText(event)
      if (content) finalContent = content
      continue
    }
    if (type === 'stream_error') {
      error = streamEventText(event)
    }
  }

  const accumulated = chunks.join('')
  if (!finalContent && done) finalContent = accumulated || formatOutputPayload(output)
  const content = finalContent || accumulated || formatOutputPayload(output)

  return {
    content,
    chunks,
    done,
    error,
    finalContent,
    streaming: chunks.length > 0 && !done && !error,
  }
}

export function formatChatflowAssistantText(
  output: Record<string, unknown> | null | undefined,
  streamPreview?: ChatflowStreamPreview | null,
): string {
  if (streamPreview?.finalContent) return streamPreview.finalContent
  if (streamPreview?.content) return streamPreview.content
  return formatOutputPayload(output)
}

function formatOutputPayload(output: Record<string, unknown> | null | undefined): string {
  const payload = output || {}
  const interrupt = payload.interrupt as Record<string, unknown> | undefined
  if (typeof interrupt?.question === 'string') return interrupt.question
  if (typeof interrupt?.followup === 'string') return interrupt.followup
  if (typeof interrupt?.prompt === 'string') return interrupt.prompt
  if (interrupt?.type === 'TRANSFER_TO_HUMAN' && typeof interrupt.message === 'string') return interrupt.message

  for (const key of ['final', 'output', 'answer', 'content']) {
    const value = payload[key]
    if (value === null || value === undefined || value === '') continue
    return typeof value === 'string' ? value : JSON.stringify(value)
  }

  return '暂无回复内容'
}

function streamEventText(event: ChatflowStreamEventLike): string {
  const payload = event.payload || {}
  for (const key of ['content', 'delta', 'text', 'message']) {
    const direct = event[key as keyof ChatflowStreamEventLike]
    if (typeof direct === 'string') return direct
    const nested = payload[key]
    if (typeof nested === 'string') return nested
  }
  return ''
}

function normalizeSuggestedQuestions(questions: string[]): string[] {
  const normalized: string[] = []
  const seen = new Set<string>()
  for (const question of questions) {
    const value = String(question || '').trim()
    if (!value || seen.has(value)) continue
    seen.add(value)
    normalized.push(value)
  }
  return normalized
}
