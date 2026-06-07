export interface ChatflowOpenShellInput {
  chatflowId: number
  channel: string
}

export interface ChatflowPublishGateInput {
  lastRunStatus: string
  dirtySinceTestRun: boolean
}

export interface ChatflowChannelShell {
  channelId: string
  displayName: string
  enabled: boolean
  runnable: boolean
  unavailableReason?: string
  deliveryCapabilities?: Record<string, boolean>
  normalizedInputFields?: string[]
  configSchema?: Record<string, unknown>
}

export interface ChatflowChannelRow {
  id: string
  name: string
  status: string
  disabled: boolean
  reason: string
  capabilities: string
  normalizedInputFields: string[]
  hasConfigSchema: boolean
}

export interface WorkflowVersionLike {
  id: number
  version: number
  active: boolean
  createdAt: string
}

export interface WorkflowVersionRow {
  id: number
  label: string
  status: string
  canRollback: boolean
  createdAt: string
}

export function buildChatflowOpenShell(input: ChatflowOpenShellInput) {
  return {
    endpoint: `/api/v1/chatflows/${input.chatflowId || '{chatflowId}'}/runs`,
    channelFields: [
      { label: '默认渠道', value: input.channel },
      { label: '调用方式', value: 'POST' },
      { label: '资源类型', value: 'CHATFLOW' },
    ],
  }
}

export function buildChatflowChannelRows(channels: ChatflowChannelShell[]): ChatflowChannelRow[] {
  return channels.map((channel) => {
    const disabled = !channel.runnable || !channel.enabled
    return {
      id: channel.channelId,
      name: channel.displayName,
      status: disabled ? '未启用' : '可运行',
      disabled,
      reason: channel.runnable ? '' : channel.unavailableReason || '',
      capabilities: formatChannelCapabilities(channel.deliveryCapabilities || {}),
      normalizedInputFields: Array.isArray(channel.normalizedInputFields) ? channel.normalizedInputFields : [],
      hasConfigSchema: Boolean(channel.configSchema && channel.configSchema.type === 'object'),
    }
  })
}

export function formatChannelCapabilities(capabilities: Record<string, boolean>) {
  const labels: Record<string, string> = {
    sync: '同步',
    streaming: '流式',
    files: '文件',
    cards: '卡片',
  }
  return Object.entries(labels)
    .filter(([key]) => capabilities[key])
    .map(([, label]) => label)
    .join(' / ') || '不可投递'
}

export function buildWorkflowVersionRows(versions: WorkflowVersionLike[]): WorkflowVersionRow[] {
  return versions.map((version) => ({
    id: version.id,
    label: `v${version.version}`,
    status: version.active ? '当前版本' : '可回滚',
    canRollback: !version.active,
    createdAt: version.createdAt,
  }))
}

export function evaluateChatflowPublishGate(input: ChatflowPublishGateInput) {
  const reasons: string[] = []

  if (input.lastRunStatus !== 'SUCCEEDED') {
    reasons.push('需要先完成一次成功试运行')
  }
  if (input.lastRunStatus === 'SUCCEEDED' && input.dirtySinceTestRun) {
    reasons.push('Chatflow 已变更，需要重新试运行')
  }

  return {
    allowed: reasons.length === 0,
    reasons,
  }
}
