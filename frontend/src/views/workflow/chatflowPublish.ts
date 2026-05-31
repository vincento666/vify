export interface ChatflowOpenShellInput {
  chatflowId: number
  channel: string
}

export interface ChatflowPublishGateInput {
  lastRunStatus: string
  dirtySinceTestRun: boolean
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
