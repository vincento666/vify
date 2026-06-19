import type { AiAssistantEvent } from '@/api/aiAssistant'

export type AiAssistantTimelineKind =
  | 'phase'
  | 'model'
  | 'model-output'
  | 'model-thought'
  | 'file'
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
  toolInvocations?: AiAssistantToolInvocation[]
}

export interface AiAssistantTimelineDetail {
  label: '调用详情' | '输入' | '输出' | '内容' | '结果'
  value: string
  monospace?: boolean
  testId?: string
}

export interface AiAssistantToolInvocation {
  id: string
  title: string
  subtitle: string
  statusText: string
  tone: AiAssistantTimelineItem['tone']
  inputRows: AiAssistantToolInvocationRow[]
  outputRows: AiAssistantToolInvocationRow[]
  displayMode?: 'rows' | 'shell'
  shellCommand?: string
  shellOutput?: string
  shellResultText?: string
  shellCopyText?: string
}

export interface AiAssistantToolInvocationRow {
  label: string
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
  const summaryItems = groupedToolTimelineItems(toolGroups)
  const summaryItemsBySequence = new Map(summaryItems.map((item) => [item.sequence, item]))
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
      const summaryItem = summaryItemsBySequence.get(event.sequence)
      if (summaryItem) timeline.push(summaryItem)
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
  const title = allShellCommands ? shellGroupsTitle(orderedGroups) : '工具调用'
  return {
    id: `${firstEvent.runId}-${firstSequence}-${lastSequence}-tool-summary`,
    eventId: resultEvent.id,
    sequence: firstSequence,
    kind: 'tool',
    tone: toolGroupsTone(orderedGroups),
    title,
    summary: allShellCommands ? title : `已汇总 ${orderedGroups.length} 次工具调用`,
    payloadPreview: compactPayload({
      callCount: orderedGroups.length,
      toolNames: orderedGroups.map((group) => group.toolName),
      statuses: orderedGroups.map((group) => group.status || toolGroupTone(group)),
      fromSequence: firstSequence,
      toSequence: lastSequence,
    }),
    details: [],
    toolInvocations: allShellCommands ? orderedGroups.map(toolGroupToInvocation) : [toolGroupsToSummaryInvocation(orderedGroups)],
  }
}

function groupedToolTimelineItems(groups: ToolEventGroup[]): AiAssistantTimelineItem[] {
  const orderedGroups = groups.slice().sort((left, right) => left.firstSequence - right.firstSequence)
  const buckets: ToolEventGroup[][] = []
  let currentBucket: ToolEventGroup[] = []
  let currentBucketType: string | null = null

  for (const group of orderedGroups) {
    const bucketType = toolBucketType(group.toolName)
    if (currentBucketType && currentBucketType !== bucketType) {
      buckets.push(currentBucket)
      currentBucket = []
    }
    currentBucket.push(group)
    currentBucketType = bucketType
  }
  if (currentBucket.length > 0) buckets.push(currentBucket)

  return buckets
    .map((bucket) => {
      if (bucket.every((group) => isFileToolName(group.toolName))) return fileGroupsToTimelineItem(bucket)
      return toolGroupsToTimelineItem(bucket)
    })
    .filter((item): item is AiAssistantTimelineItem => Boolean(item))
}

function fileGroupsToTimelineItem(groups: ToolEventGroup[]): AiAssistantTimelineItem | undefined {
  if (groups.length === 0) return undefined
  const orderedGroups = groups.slice().sort((left, right) => left.firstSequence - right.firstSequence)
  const events = orderedGroups.flatMap((group) => group.events).sort((left, right) => left.sequence - right.sequence)
  const firstEvent = events[0]
  const resultEvent = events[events.length - 1]
  const firstSequence = Math.min(...orderedGroups.map((group) => group.firstSequence))
  const lastSequence = Math.max(...orderedGroups.map((group) => group.lastSequence))
  const title = fileGroupsTitle(orderedGroups)
  return {
    id: `${firstEvent.runId}-${firstSequence}-${lastSequence}-file-summary`,
    eventId: resultEvent.id,
    sequence: firstSequence,
    kind: 'file',
    tone: toolGroupsTone(orderedGroups),
    title,
    summary: title,
    payloadPreview: compactPayload({
      fileCount: uniqueFilePaths(orderedGroups).length || orderedGroups.length,
      operations: orderedGroups.map((group) => group.toolName),
      statuses: orderedGroups.map((group) => group.status || toolGroupTone(group)),
      fromSequence: firstSequence,
      toSequence: lastSequence,
    }),
    details: fileGroupsToDetails(orderedGroups),
  }
}

function toolBucketType(toolName: string) {
  if (toolName === 'read_workspace_file') return 'file-read'
  if (toolName === 'write_workspace_file') return 'file-write'
  if (toolName === 'create_workspace_file') return 'file-create'
  return 'tool'
}

function isFileToolName(toolName: string) {
  return toolBucketType(toolName).startsWith('file-')
}

function fileGroupsTitle(groups: ToolEventGroup[]) {
  const count = uniqueFilePaths(groups).length || groups.length
  if (groups.every((group) => group.toolName === 'read_workspace_file')) return `已读取 ${count} 个文件`
  if (groups.every((group) => group.toolName === 'create_workspace_file')) return `已创建 ${count} 个文件`
  if (groups.every((group) => group.toolName === 'write_workspace_file')) return `已编辑 ${count} 个文件`
  return `已处理 ${count} 个文件`
}

function shellGroupsTitle(groups: ToolEventGroup[]) {
  return `已运行 ${groups.length} 条命令`
}

function fileGroupsToDetails(groups: ToolEventGroup[]): AiAssistantTimelineDetail[] {
  const input = uniqueBlocks(
    groups.map((group) => {
      const rows = toolInputRows(group)
      return rowsToBlock(rows)
    }),
  ).join('\n\n')
  const output = uniqueBlocks(
    groups.map((group) => {
      const rows = toolOutputRows(group)
      return rowsToBlock(rows)
    }),
  ).join('\n\n')
  const details: AiAssistantTimelineDetail[] = [
    { label: '输入', value: input, monospace: true },
    { label: '结果', value: output, monospace: true },
  ]
  return details.filter((row) => row.value.trim() !== '')
}

function uniqueBlocks(blocks: string[]) {
  return Array.from(new Set(blocks.map((block) => block.trim()).filter(Boolean)))
}

function uniqueFilePaths(groups: ToolEventGroup[]) {
  return Array.from(
    new Set(
      groups
        .map((group) => workspacePathFromValue(group.input) || workspacePathFromValue(group.output))
        .filter(Boolean),
    ),
  )
}

function toolGroupsToSummaryInvocation(groups: ToolEventGroup): AiAssistantToolInvocation
function toolGroupsToSummaryInvocation(groups: ToolEventGroup[]): AiAssistantToolInvocation
function toolGroupsToSummaryInvocation(groups: ToolEventGroup | ToolEventGroup[]): AiAssistantToolInvocation {
  const orderedGroups = (Array.isArray(groups) ? groups : [groups]).slice().sort((left, right) => left.firstSequence - right.firstSequence)
  const invocations = orderedGroups.map(toolGroupToInvocation)
  const first = orderedGroups[0]
  const single = invocations.length === 1 ? invocations[0] : undefined
  return {
    id: `${first.id}-summary`,
    title: toolSummaryTitle(invocations),
    subtitle: single?.subtitle || `${invocations.length} 个工具`,
    statusText: toolGroupsStatusText(orderedGroups),
    tone: toolGroupsTone(orderedGroups),
    inputRows: toolSummaryInputRows(invocations),
    outputRows: toolSummaryOutputRows(invocations),
  }
}

function toolSummaryTitle(invocations: AiAssistantToolInvocation[]) {
  const titles = Array.from(new Set(invocations.map((invocation) => invocation.title).filter(Boolean)))
  if (titles.length === 0) return '工具调用'
  if (titles.length <= 3) return titles.join('、')
  return `${titles.slice(0, 3).join('、')}等 ${titles.length} 个工具`
}

function toolGroupsStatusText(groups: ToolEventGroup[]) {
  if (groups.some((group) => toolGroupTone(group) === 'danger')) return '失败'
  if (groups.some((group) => toolGroupTone(group) === 'running')) return '运行中'
  if (groups.length === 1) return toolInvocationStatusText(groups[0])
  return '已完成'
}

function toolSummaryInputRows(invocations: AiAssistantToolInvocation[]): AiAssistantToolInvocationRow[] {
  return [
    {
      label: '调用工具',
      value: invocations.map(invocationSummaryLine).join('\n'),
      monospace: true,
    },
    ...invocations
      .filter((invocation) => invocation.inputRows.length > 0)
      .map((invocation) => ({
        label: invocationSectionLabel(invocation),
        value: rowsToBlock(invocation.inputRows),
        monospace: true,
      })),
  ]
}

function toolSummaryOutputRows(invocations: AiAssistantToolInvocation[]): AiAssistantToolInvocationRow[] {
  return invocations
    .filter((invocation) => invocation.outputRows.length > 0)
    .map((invocation) => ({
      label: invocationSectionLabel(invocation),
      value: rowsToBlock(invocation.outputRows),
      monospace: true,
    }))
}

function invocationSummaryLine(invocation: AiAssistantToolInvocation) {
  const subject = invocation.subtitle ? `${invocation.title}：${invocation.subtitle}` : invocation.title
  return `${subject}（${invocation.statusText}）`
}

function invocationSectionLabel(invocation: AiAssistantToolInvocation) {
  return invocation.subtitle ? `${invocation.title} · ${invocation.subtitle}` : invocation.title
}

function rowsToBlock(rows: AiAssistantToolInvocationRow[]) {
  return rows.map((row) => `${row.label}：${row.value}`).join('\n')
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

function toolGroupToInvocation(group: ToolEventGroup): AiAssistantToolInvocation {
  if (group.toolName === 'run_shell') return shellGroupToInvocation(group)
  return {
    id: group.id,
    title: toolDisplayName(group.toolName),
    subtitle: toolInvocationSubtitle(group),
    statusText: toolInvocationStatusText(group),
    tone: toolGroupTone(group),
    inputRows: toolInputRows(group),
    outputRows: toolOutputRows(group),
  }
}

function shellGroupToInvocation(group: ToolEventGroup): AiAssistantToolInvocation {
  const command = shellCommandText(group)
  const output = shellOutputText(group)
  const resultText = shellResultText(group)
  return {
    id: group.id,
    title: command || '命令',
    subtitle: '',
    statusText: toolInvocationStatusText(group),
    tone: toolGroupTone(group),
    inputRows: [],
    outputRows: [],
    displayMode: 'shell',
    shellCommand: command,
    shellOutput: output,
    shellResultText: resultText,
    shellCopyText: shellCopyText(command, output),
  }
}

function shellCommandText(group: ToolEventGroup) {
  return (
    fieldValue(group.input, 'command') ||
    fieldValue(group.input, 'args') ||
    fieldValue(group.output, 'command') ||
    fieldValue(group.output, 'args')
  )
}

function shellOutputText(group: ToolEventGroup) {
  const stdout = fieldValue(group.output, 'stdout')
  const stderr = fieldValue(group.output, 'stderr')
  const message = !stdout && !stderr ? summarizeToolOutput(group.toolName, group.output) : ''
  return [stdout, stderr, message].filter(Boolean).join('\n').trim()
}

function shellResultText(group: ToolEventGroup) {
  const tone = toolGroupTone(group)
  const exitCode = Number(fieldValue(group.output, 'exitCode'))
  if (tone === 'running') return '运行中'
  if (tone === 'danger' || (!Number.isNaN(exitCode) && exitCode !== 0)) return '失败'
  return '成功'
}

function shellCopyText(command: string, output: string) {
  return [`$ ${command}`.trim(), output].filter(Boolean).join('\n\n')
}

function toolInvocationSubtitle(group: ToolEventGroup) {
  if (group.toolName === 'invoke_skill') return fieldValue(group.input, 'skillName') || fieldValue(group.output, 'skillName')
  if (group.toolName === 'search_knowledge_base') return fieldValue(group.input, 'query') || fieldValue(group.output, 'query')
  if (group.toolName === 'run_shell') return truncateInline(fieldValue(group.input, 'command') || fieldValue(group.input, 'args'))
  return fieldValue(group.input, 'path') || fieldValue(group.output, 'path') || toolInvocationStatusText(group)
}

function toolInvocationStatusText(group: ToolEventGroup) {
  const outputStatus = fieldValue(group.output, 'status')
  if (group.toolName === 'invoke_skill' && outputStatus === 'RECORDED') return '已记录'
  if (group.status === 'NOT_FOUND') return '未找到'
  if (group.status === 'FAILED') return '失败'
  if (group.completed || group.output !== undefined) return '已完成'
  return '运行中'
}

function toolInputRows(group: ToolEventGroup): AiAssistantToolInvocationRow[] {
  const input = group.input
  if (!isRecord(input)) return input === undefined ? [] : [{ label: '输入', value: truncateInline(String(input)) }]
  if (group.toolName === 'invoke_skill') {
    return compactRows([
      ['技能', fieldValue(input, 'skillName')],
      ['说明', fieldValue(input, 'instruction')],
    ])
  }
  if (group.toolName === 'search_knowledge_base') {
    return compactRows([
      ['查询', fieldValue(input, 'query')],
      ['知识库', fieldValue(input, 'knowledgeBaseId')],
      ['数量', fieldValue(input, 'limit')],
    ])
  }
  if (group.toolName === 'write_workspace_file') {
    return compactRows([
      ['路径', fieldValue(input, 'path')],
      ['内容预览', truncateBlock(fieldValue(input, 'content')), true],
    ])
  }
  if (group.toolName === 'read_workspace_file') {
    return compactRows([['路径', fieldValue(input, 'path')]])
  }
  if (group.toolName === 'run_shell') {
    return compactRows([
      ['命令', fieldValue(input, 'command') || fieldValue(input, 'args'), true],
      ['工作目录', fieldValue(input, 'cwd')],
    ])
  }
  return objectRows(input, '输入')
}

function toolOutputRows(group: ToolEventGroup): AiAssistantToolInvocationRow[] {
  const output = group.output
  if (group.toolName === 'invoke_skill') {
    return compactRows([
      ['结果', group.output === undefined ? summarizeToolStatus(group) || '等待结果' : '已记录技能意图'],
      ['说明', fieldValue(output, 'instruction')],
    ])
  }
  if (group.toolName === 'search_knowledge_base') {
    const hits = isRecord(output) && Array.isArray(output.hits) ? output.hits.length : undefined
    return compactRows([
      ['结果', hits === undefined ? summarizeToolStatus(group) || '等待结果' : `命中 ${hits} 条`],
      ['来源', fieldValue(output, 'source')],
    ])
  }
  if (group.toolName === 'read_workspace_file') {
    const status = summarizeToolStatus(group)
    const content = fieldValue(output, 'content') || fieldValue(output, 'text')
    return compactRows([
      ['结果', content ? `已读取 ${fieldValue(output, 'path') || toolInvocationSubtitle(group)}` : status || '等待结果'],
      ['内容预览', truncateBlock(content), true],
    ])
  }
  if (group.toolName === 'write_workspace_file') {
    return compactRows([['结果', summarizeToolOutput(group.toolName, output) || summarizeToolStatus(group) || '等待结果']])
  }
  if (group.toolName === 'run_shell') {
    const stdout = fieldValue(output, 'stdout')
    const stderr = fieldValue(output, 'stderr')
    const result = summarizeToolStatus(group) || (!stdout && !stderr ? summarizeToolOutput(group.toolName, output) : '')
    return compactRows([
      ['输出', truncateBlock(stdout), true],
      ['错误', truncateBlock(stderr), true],
      ['结果', result || (!stdout && !stderr ? '等待结果' : '')],
    ])
  }
  const summary = summarizeToolOutput(group.toolName, output) || summarizeToolStatus(group) || '等待结果'
  return output === undefined ? [{ label: '结果', value: summary }] : objectRows(output, '输出', summary)
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

function compactRows(rows: Array<[string, string | number | undefined, boolean?]>): AiAssistantToolInvocationRow[] {
  return rows
    .map(([label, value, monospace]) => ({
      label,
      value: value === undefined || value === null ? '' : String(value).trim(),
      monospace,
    }))
    .filter((row) => row.value !== '')
}

function objectRows(value: unknown, fallbackLabel: string, summary?: string): AiAssistantToolInvocationRow[] {
  if (!isRecord(value)) return summary ? [{ label: '结果', value: summary }] : []
  const rows = Object.entries(value)
    .map(([key, rowValue]) => ({
      label: readableFieldLabel(key, fallbackLabel),
      value: formatFieldValue(rowValue),
      monospace: typeof rowValue === 'object' && rowValue !== null,
    }))
    .filter((row) => row.value !== '')
  return summary && rows.length === 0 ? [{ label: '结果', value: summary }] : rows
}

function readableFieldLabel(key: string, fallbackLabel: string) {
  const labels: Record<string, string> = {
    path: '路径',
    content: '内容预览',
    text: '内容',
    stdout: '输出',
    stderr: '错误',
    message: '消息',
    status: '状态',
    query: '查询',
    source: '来源',
    hits: '命中',
    bytes: '字节',
    skillName: '技能',
    instruction: '说明',
  }
  return labels[key] || fallbackLabel
}

function formatFieldValue(value: unknown) {
  if (value === undefined || value === null) return ''
  if (typeof value === 'string') return truncateBlock(value)
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return value.length === 0 ? '0 条' : truncateBlock(prettyPayload(value))
  return truncateBlock(prettyPayload(value))
}

function fieldValue(value: unknown, key: string) {
  if (!isRecord(value)) return ''
  const raw = value[key]
  if (raw === undefined || raw === null) return ''
  if (typeof raw === 'string') return raw.trim()
  if (typeof raw === 'number' || typeof raw === 'boolean') return String(raw)
  return prettyPayload(raw)
}

function toolDisplayName(toolName: string) {
  const labels: Record<string, string> = {
    read_workspace_file: '读取工作区文件',
    write_workspace_file: '写入工作区文件',
    search_knowledge_base: '知识库检索',
    invoke_skill: '使用技能',
    run_shell: '终端命令',
  }
  return labels[toolName] || '工具调用'
}

function truncateBlock(value: string) {
  const text = value.trim()
  if (text.length <= 600) return text
  return `${text.slice(0, 597)}...`
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
