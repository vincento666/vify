export interface ChatflowVariableItem {
  label: string
  name: string
  type: string
  reference: string
}

export interface ChatflowVariableScope {
  title: string
  description: string
  items: ChatflowVariableItem[]
}

export function buildChatflowVariableScopes(): ChatflowVariableScope[] {
  return [
    {
      title: '运行上下文',
      description: '试运行或渠道调用时注入',
      items: [
        variable('当前消息', 'sys.query'),
        variable('会话 ID', 'sys.conversation_id'),
        variable('会话名称', 'sys.conversation_name'),
        variable('用户 ID', 'sys.user_id'),
        variable('渠道', 'sys.channel'),
        variable('渠道 ID', 'sys.channel_id'),
        variable('当前时间', 'sys.now'),
        variable('消息 ID', 'sys.message_id'),
        variable('对话轮次', 'sys.round', 'number'),
        variable('上传文件', 'sys.files', 'array'),
      ],
    },
  ]
}

export function insertChatflowVariableReference(currentValue: string, reference: string) {
  return currentValue.trim() ? `${currentValue} ${reference}` : reference
}

function variable(label: string, name: string, type = 'string'): ChatflowVariableItem {
  return {
    label,
    name,
    type,
    reference: `{{${name}}}`,
  }
}
