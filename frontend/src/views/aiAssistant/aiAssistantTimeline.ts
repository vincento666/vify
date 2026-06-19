import type { AiAssistantEvent } from '@/api/aiAssistant'

export type AiAssistantTimelineKind =
  | 'phase'
  | 'model'
  | 'model-output'
  | 'model-thought'
  | 'tool'
  | 'tool-output'
  | 'approval'
  | 'sandbox'
  | 'proposed-action'
  | 'result'
  | 'error'

export interface AiAssistantTimelineItem {
  id: string
  eventId: number
  sequence: number
  kind: AiAssistantTimelineKind
  tone: 'running' | 'success' | 'waiting' | 'danger' | 'neutral'
  title: string
  summary: string
  payloadPreview: string
  details: AiAssistantTimelineDetail[]
  approvalId?: number
  phase?: string
  source?: string
}

export interface AiAssistantTimelineDetail {
  label: '调用详情' | '输入' | '输出' | '内容' | '结果'
  value: string
  monospace?: boolean
  testId?: string
}

interface ToolEventGroup {
  id: string
  key: string
  events: AiAssistantEvent[]
  toolName: string
  input?: unknown
  output?: unknown
  status?: string
  completed: boolean
  firstSequence: number
  lastSequence: number
}

export function buildAiAssistantTimeline(events: AiAssistantEvent[]): AiAssistantTimelineItem[] {
  const sortedEvents = events.slice().sort((left, right) => left.sequence - right.sequence)
  const toolGroups = collectToolGroups(sortedEvents)
  const toolSummaryItem = toolGroupsToTimelineItem(toolGroups)
  const toolSummarySequence = toolSummaryItem?.sequence
  let renderedToolSummary = false
  const toolEventSequences = new Set(toolGroups.flatMap((group) => group.events.map((event) => event.sequence)))
  const timeline: AiAssistantTimelineItem[] = []
  let modelStreamGroup: AiAssistantEvent[] = []
  let lastModelOutput = ''

  for (let index = 0; index < sortedEvents.length; index += 1) {
    const event = sortedEvents[index]
    if (event.type === 'model.stream_chunk') {
      modelStreamGroup.push(event)
      continue
    }

    lastModelOutput = flushModelStreamGroup(timeline, modelStreamGroup, lastModelOutput)
    modelStreamGroup = []

    if (toolEventSequences.has(event.sequence)) {
      if (toolSummaryItem && !renderedToolSummary && event.sequence === toolSummarySequence) {
        timeline.push(toolSummaryItem)
        renderedToolSummary = true
      }
      continue
    }

    if (
      event.type === 'model.thought_summary' &&
      (isDuplicateThought(event, lastModelOutput) || isDuplicateThought(event, nextModelStreamSummary(sortedEvents, index)))
    ) {
      continue
    }

    if (shouldRenderEvent(event)) timeline.push(eventToTimelineItem(event))
  }
  flushModelStreamGroup(timeline, modelStreamGroup, lastModelOutput)
  return timeline
}

function eventToTimelineItem(event: AiAssistantEvent): AiAssistantTimelineItem {
  const kind = eventKind(event.type)
  const summary = normalizeRepeatedText(event.visibleSummary || '')
  return {
    id: `${event.runId}-${event.sequence}-${event.type}`,
    eventId: event.id,
    sequence: event.sequence,
    kind,
    tone: eventTone(event),
    title: timelineTitle(event, kind),
    summary,
    payloadPreview: compactPayload(event.payload),
    details: eventDetails(event, kind, summary),
    approvalId: typeof event.payload?.approvalId === 'number' ? event.payload.approvalId : undefined,
  }
}

function flushModelStreamGroup(
  timeline: AiAssistantTimelineItem[],
  events: AiAssistantEvent[],
  previousModelOutput: string,
) {
  if (events.length === 0) return previousModelOutput
  const first = events[0]
  const last = events[events.length - 1]
  const summary = normalizeRepeatedText(events.map(modelStreamChunkText).join(''))
  timeline.push({
    id: `${first.runId}-${first.sequence}-${last.sequence}-model.stream_chunk`,
    eventId: last.id,
    sequence: first.sequence,
    kind: 'model-output',
    tone: modelStreamTone(events),
    title: '模型输出',
    summary,
    payloadPreview: compactPayload({
      chunkCount: events.length,
      fromSequence: first.sequence,
      toSequence: last.sequence,
      phase: first.payload?.phase,
      source: first.payload?.source,
      streaming: events.some((event) => event.payload?.streaming === true),
    }),
    details: [
      {
        label: '调用详情',
        value: `流式片段 ${events.length} 段${first.payload?.source ? ` / ${String(first.payload.source)}` : ''}`,
      },
      { label: '内容', value: summary, monospace: true },
    ],
    phase: typeof first.payload?.phase === 'string' ? first.payload.phase : undefined,
    source: typeof first.payload?.source === 'string' ? first.payload.source : undefined,
  })
  return summary
}

function modelStreamChunkText(event: AiAssistantEvent) {
  const chunk = event.payload?.chunk
  return typeof chunk === 'string' ? chunk : event.visibleSummary || ''
}

function modelStreamTone(events: AiAssistantEvent[]): AiAssistantTimelineItem['tone'] {
  if (events.some((event) => event.status === 'WAITING')) return 'waiting'
  if (events.some((event) => event.status === 'RUNNING')) return 'running'
  return 'success'
}

function eventKind(type: string): AiAssistantTimelineKind {
  if (type.startsWith('orchestration.') || type === 'run.started') return 'phase'
  if (type === 'model.stream_chunk') return 'model-output'
  if (type === 'model.thought_summary') return 'model-thought'
  if (type.startsWith('model.')) return 'model'
  if (type === 'tool.call_output') return 'tool-output'
  if (type.startsWith('tool.')) return 'tool'
  if (type.startsWith('approval.')) return 'approval'
  if (type === 'sandbox.denied') return 'sandbox'
  if (type.startsWith('proposed_action.')) return 'proposed-action'
  if (type === 'run.completed') return 'result'
  if (type === 'run.failed') return 'error'
  return 'phase'
}

function eventTone(event: AiAssistantEvent): AiAssistantTimelineItem['tone'] {
  if (event.type === 'model.stream_chunk') return 'running'
  if (event.type === 'run.started' || event.type.endsWith('_started')) return 'running'
  if (event.status === 'WAITING' || event.type === 'approval.required') return 'waiting'
  if (event.status === 'DENIED' || event.type === 'sandbox.denied' || event.type === 'run.failed') return 'danger'
  if (event.type === 'run.completed' || event.type.endsWith('_completed')) return 'success'
  return 'neutral'
}

function timelineTitle(event: AiAssistantEvent, kind: AiAssistantTimelineKind) {
  if (kind === 'model-thought') return '思考过程'
  if (kind === 'approval') return '审批通过'
  return event.visibleTitle || event.type
}

function eventDetails(
  event: AiAssistantEvent,
  kind: AiAssistantTimelineKind,
  summary: string,
): AiAssistantTimelineDetail[] {
  if (kind === 'model-output' || kind === 'model-thought') {
    return summary ? [{ label: '内容', value: summary, monospace: true }] : []
  }
  if (kind === 'approval') {
    return summary ? [{ label: '内容', value: summary }] : []
  }
  const rows: AiAssistantTimelineDetail[] = []
  if (summary) rows.push({ label: '调用详情', value: summary })
  if (event.payload && Object.keys(event.payload).length > 0) {
    rows.push({ label: '输入', value: prettyPayload(event.payload), monospace: true })
  }
  return rows
}

function collectToolGroups(events: AiAssistantEvent[]) {
  const groups: ToolEventGroup[] = []
  const activeGroups = new Map<string, ToolEventGroup>()
  for (const event of events) {
    if (!event.type.startsWith('tool.')) continue
    const key = toolEventKey(event)
    let group = activeGroups.get(key)
    if (!group && event.type !== 'tool.call_started') {
      group = findActiveToolGroup(activeGroups, event)
    }
    if (event.type === 'tool.call_started' || !group) {
      group = createToolGroup(event, key)
      groups.push(group)
      activeGroups.set(key, group)
    }
    if (!group.events.some((item) => item.id === event.id)) group.events.push(event)
    group.lastSequence = Math.max(group.lastSequence, event.sequence)
    mergeToolEvent(group, event)
    if (event.type === 'tool.call_completed') {
      group.completed = true
      deleteActiveToolGroup(activeGroups, group)
    }
  }
  return groups
}

function findActiveToolGroup(activeGroups: Map<string, ToolEventGroup>, event: AiAssistantEvent) {
  const toolName = payloadString(event, 'toolName')
  if (!toolName) return undefined
  return Array.from(new Set(activeGroups.values()))
    .filter((group) => !group.completed && group.toolName === toolName)
    .sort((left, right) => right.lastSequence - left.lastSequence)[0]
}

function deleteActiveToolGroup(activeGroups: Map<string, ToolEventGroup>, completedGroup: ToolEventGroup) {
  for (const [key, group] of activeGroups.entries()) {
    if (group === completedGroup) activeGroups.delete(key)
  }
}

function createToolGroup(event: AiAssistantEvent, key: string): ToolEventGroup {
  const toolName = payloadString(event, 'toolName') || 'tool'
  return {
    id: `${event.runId}-${event.sequence}-${key}-tool-call`,
    key,
    events: [],
    toolName,
    completed: false,
    firstSequence: event.sequence,
    lastSequence: event.sequence,
  }
}

function mergeToolEvent(group: ToolEventGroup, event: AiAssistantEvent) {
  group.toolName = payloadString(event, 'toolName') || group.toolName
  if ('input' in event.payload) group.input = event.payload.input
  if ('output' in event.payload) group.output = event.payload.output
  if ('status' in event.payload && typeof event.payload.status === 'string') group.status = event.payload.status
}

function toolGroupsToTimelineItem(groups: ToolEventGroup[]): AiAssistantTimelineItem | undefined {
  if (groups.length === 0) return undefined
  const orderedGroups = groups.slice().sort((left, right) => left.firstSequence - right.firstSequence)
  const events = orderedGroups.flatMap((group) => group.events).sort((left, right) => left.sequence - right.sequence)
  const firstEvent = events[0]
  const resultEvent = events[events.length - 1]
  const firstSequence = Math.min(...orderedGroups.map((group) => group.firstSequence))
  const lastSequence = Math.max(...orderedGroups.map((group) => group.lastSequence))
  const allShellCommands = orderedGroups.every((group) => group.toolName === 'run_shell')
  return {
    id: `${firstEvent.runId}-${firstSequence}-${lastSequence}-tool-summary`,
    eventId: resultEvent.id,
    sequence: firstSequence,
    kind: 'tool',
    tone: toolGroupsTone(orderedGroups),
    title: allShellCommands ? '命令执行' : '工具调用',
    summary: `已汇总 ${orderedGroups.length} 次工具调用`,
    payloadPreview: compactPayload({
      callCount: orderedGroups.length,
      toolNames: orderedGroups.map((group) => group.toolName),
      statuses: orderedGroups.map((group) => group.status || toolGroupTone(group)),
      fromSequence: firstSequence,
      toSequence: lastSequence,
    }),
    details: [
      {
        label: '结果',
        value: summarizeToolGroups(orderedGroups),
        monospace: true,
        testId: 'ai-assistant-tool-detail-output',
      },
    ],
  }
}


function shouldRenderEvent(event: AiAssistantEvent) {
  if (event.type === 'model.thought_summary') return true
  if (event.type === 'approval.approved') return true
  return false
}

function toolGroupTone(group: ToolEventGroup): AiAssistantTimelineItem['tone'] {
  if (group.status === 'FAILED') return 'danger'
  if (group.completed || group.output !== undefined) return 'success'
  return 'running'
}

function toolGroupsTone(groups: ToolEventGroup[]): AiAssistantTimelineItem['tone'] {
  if (groups.some((group) => toolGroupTone(group) === 'danger')) return 'danger'
  if (groups.some((group) => toolGroupTone(group) === 'running')) return 'running'
  return 'success'
}

function toolEventKey(event: AiAssistantEvent) {
  const scheduler = event.payload?.scheduler ?? event.correlationIds?.scheduler
  if (scheduler) return `${payloadString(event, 'toolName')}:${JSON.stringify(scheduler)}`
  if (event.toolCallId) return `tool-call:${event.toolCallId}`
  return payloadString(event, 'toolName') || `tool-sequence:${event.sequence}`
}

function summarizeToolOutput(toolName: string, output: unknown) {
  if (output === undefined || output === null) return ''
  if (typeof output === 'string') return output
  if (!isRecord(output)) return String(output)
  if (toolName === 'read_workspace_file') return stringValue(output.content) || stringValue(output.text) || stringValue(output.echo)
  if (toolName === 'write_workspace_file') {
    const path = stringValue(output.path)
    const bytes = typeof output.bytes === 'number' ? output.bytes : undefined
    if (path && bytes !== undefined) return `已写入 ${path}（${bytes} bytes）`
    if (path) return `已写入 ${path}`
  }
  if (toolName === 'invoke_skill') {
    const skillName = stringValue(output.skillName)
    const instruction = stringValue(output.instruction)
    return [`已记录技能 ${skillName}`, instruction].filter(Boolean).join('：')
  }
  if (toolName === 'search_knowledge_base') {
    const query = stringValue(output.query)
    const hits = Array.isArray(output.hits) ? output.hits.length : 0
    return `知识库检索：${query || '未命名查询'}，命中 ${hits} 条`
  }
  return (
    stringValue(output.content) ||
    stringValue(output.text) ||
    stringValue(output.echo) ||
    stringValue(output.stdout) ||
    stringValue(output.stderr) ||
    stringValue(output.message) ||
    prettyPayload(output)
  )
}

function summarizeToolGroups(groups: ToolEventGroup[]) {
  return groups
    .map((group) => {
      const rows = [toolDisplayName(group.toolName)]
      const input = summarizeToolInput(group.toolName, group.input)
      if (input) rows.push(`输入：${input}`)
      rows.push(`输出：${summarizeToolOutput(group.toolName, group.output) || summarizeToolStatus(group) || '等待结果'}`)
      return rows.join('\n')
    })
    .join('\n\n')
}

function summarizeToolStatus(group: ToolEventGroup) {
  if (!group.completed && group.status !== 'FAILED') return ''
  const path = workspacePathFromValue(group.input) || workspacePathFromValue(group.output)
  if (group.status === 'NOT_FOUND') return path ? `未找到 ${path}` : '未找到'
  if (group.status === 'FAILED') return '执行失败'
  if (group.completed) return '已完成'
  return ''
}

function workspacePathFromValue(value: unknown) {
  return isRecord(value) ? stringValue(value.path) : ''
}

function summarizeToolInput(toolName: string, input: unknown) {
  if (input === undefined || input === null) return ''
  if (typeof input === 'string') return truncateInline(input)
  if (!isRecord(input)) return truncateInline(String(input))

  const path = stringValue(input.path)
  const query = stringValue(input.query)
  const command = stringValue(input.command)
  const skillName = stringValue(input.skillName)
  const instruction = stringValue(input.instruction)
  const content = stringValue(input.content)
  const message = stringValue(input.message)
  const args = stringValue(input.args)
  const parts: string[] = []

  if (toolName === 'run_shell' && command) parts.push(`command=${command}`)
  else if (path) parts.push(`path=${path}`)
  if (query) parts.push(`query=${query}`)
  if (skillName) parts.push(`skill=${skillName}`)
  if (instruction) parts.push(`instruction=${truncateInline(instruction)}`)
  if (message) parts.push(`message=${truncateInline(message)}`)
  if (args) parts.push(`args=${truncateInline(args)}`)
  if (content) parts.push(`content=${truncateInline(content)}`)

  if (parts.length > 0) return parts.join('，')
  return truncateInline(prettyPayload(input).replace(/[{}\n"]/g, ' ').replace(/\s+/g, ' ').trim())
}

function toolDisplayName(toolName: string) {
  const labels: Record<string, string> = {
    read_workspace_file: '读取工作区文件',
    write_workspace_file: '写入工作区文件',
    search_knowledge_base: '知识库检索',
    invoke_skill: '技能调用',
    run_shell: '终端命令',
  }
  return labels[toolName] || '工具调用'
}

function truncateInline(value: string) {
  const text = value.replace(/\s+/g, ' ').trim()
  if (text.length <= 120) return text
  return `${text.slice(0, 117)}...`
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}

function payloadString(event: AiAssistantEvent, key: string) {
  const value = event.payload?.[key]
  return typeof value === 'string' ? value : ''
}

function isDuplicateThought(event: AiAssistantEvent, lastModelOutput: string) {
  const summary = String(event.payload?.summary || event.visibleSummary || '')
  return normalizeText(summary) !== '' && normalizeText(summary) === normalizeText(lastModelOutput)
}

function nextModelStreamSummary(events: AiAssistantEvent[], currentIndex: number) {
  const chunks: string[] = []
  for (let index = currentIndex + 1; index < events.length; index += 1) {
    const event = events[index]
    if (event.type !== 'model.stream_chunk') break
    chunks.push(modelStreamChunkText(event))
  }
  return chunks.join('')
}

function normalizeText(value: string) {
  return value.replace(/\s+/g, '').trim()
}

function normalizeRepeatedText(value: string) {
  let text = value.trim()
  for (let index = 0; index < 4; index += 1) {
    const collapsed = collapseAdjacentRepeatedUnits(text)
    if (collapsed === text) break
    text = collapsed
  }
  return text
}

function collapseAdjacentRepeatedUnits(text: string) {
  let output = ''
  let index = 0
  while (index < text.length) {
    const maxUnitLength = Math.min(32, Math.floor((text.length - index) / 2))
    let matched = false
    for (let unitLength = maxUnitLength; unitLength > 1; unitLength -= 1) {
      const unit = text.slice(index, index + unitLength)
      if (!hasTextSignal(unit)) continue
      const nextUnit = text.slice(index + unitLength, index + unitLength * 2)
      if (unit === nextUnit) {
        output += unit
        index += unitLength * 2
        matched = true
        break
      }
    }
    if (!matched) {
      output += text[index]
      index += 1
    }
  }
  return output
}

function hasTextSignal(value: string) {
  return /[\p{L}\p{N}_]/u.test(value)
}

function compactPayload(payload: Record<string, unknown>) {
  const text = JSON.stringify(payload ?? {})
  if (text.length <= 180) return text
  return `${text.slice(0, 177)}...`
}

function prettyPayload(payload: unknown) {
  if (payload === undefined || payload === null) return ''
  if (typeof payload === 'string') return payload
  return JSON.stringify(payload, null, 2)
}
