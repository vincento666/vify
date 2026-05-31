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
      title: 'System',
      description: '平台为当前对话轮次注入',
      items: [
        variable('当前消息', 'sys.query'),
        variable('会话 ID', 'sys.conversation_id'),
        variable('会话名称', 'sys.conversation_name'),
        variable('用户 ID', 'sys.user_id'),
        variable('渠道', 'sys.channel'),
        variable('当前时间', 'sys.now'),
        variable('消息 ID', 'sys.message_id'),
        variable('对话轮次', 'sys.round', 'number'),
        variable('上传文件', 'sys.files', 'array'),
      ],
    },
    {
      title: 'Global',
      description: 'Chatflow 级共享变量',
      items: [variable('品牌名称', 'global.brand'), variable('默认语言', 'global.locale')],
    },
    {
      title: 'Conversation',
      description: '当前会话短期变量',
      items: [variable('当前主题', 'conversation.topic'), variable('上一轮消息', 'conversation.last_message')],
    },
    {
      title: 'User',
      description: '当前用户画像变量',
      items: [variable('用户名称', 'user.name'), variable('会员等级', 'user.vip_level')],
    },
    {
      title: 'Channel',
      description: '渠道配置变量',
      items: [variable('渠道名称', 'channel.name'), variable('来源应用', 'channel.source')],
    },
    {
      title: 'External Input',
      description: 'API 或 SDK 调用传入',
      items: [variable('输入载荷', 'input.payload', 'object'), variable('追踪 ID', 'input.trace_id')],
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
