export interface ChatflowVariableItem {
  key: string
  label: string
  name: string
  type: string
  reference: string
  readonly: boolean
}

export interface ChatflowVariableScope {
  title: string
  description: string
  scope: 'conversation' | 'user'
  items: ChatflowVariableItem[]
}

export interface ChatflowVariableDefinition {
  name: string
  label?: string
  type?: string
}

export interface ChatflowVariableScopeOptions {
  conversationVariables?: ChatflowVariableDefinition[]
  userVariables?: ChatflowVariableDefinition[]
}

export function buildChatflowVariableScopes(options: ChatflowVariableScopeOptions = {}): ChatflowVariableScope[] {
  return [
    {
      title: '会话变量',
      description: '试运行、API 或渠道调用时随会话注入',
      scope: 'conversation',
      items: [
        variable('本轮输入', 'sys.query', 'string', 'SYS_QUERY'),
        variable('会话 ID', 'sys.conversation_id', 'string', 'SYS_CONVERSATION_ID'),
        variable('会话名称', 'sys.conversation_name', 'string', 'SYS_CONVERSATION_NAME'),
        variable('用户 ID', 'sys.user_id', 'string', 'SYS_USER_ID'),
        variable('渠道', 'sys.channel', 'string', 'SYS_CHANNEL'),
        variable('渠道 ID', 'sys.channel_id', 'string', 'SYS_CHANNEL_ID'),
        variable('当前时间', 'sys.now', 'string', 'SYS_NOW'),
        variable('消息 ID', 'sys.message_id', 'string', 'SYS_MESSAGE_ID'),
        variable('对话轮次', 'sys.round', 'number', 'SYS_ROUND'),
        variable('上传文件', 'sys.files', 'array', 'SYS_FILES'),
        ...configuredVariables('conversation', options.conversationVariables),
      ],
    },
    {
      title: '用户变量',
      description: '用于长期保存用户偏好、画像信息或跨会话上下文',
      scope: 'user',
      items: configuredVariables('user', options.userVariables),
    },
  ]
}

export function insertChatflowVariableReference(currentValue: string, reference: string) {
  return currentValue.trim() ? `${currentValue} ${reference}` : reference
}

function variable(label: string, name: string, type = 'string', key = name.toUpperCase().replace(/\./g, '_')): ChatflowVariableItem {
  return {
    key,
    label,
    name,
    type,
    reference: `{{${name}}}`,
    readonly: true,
  }
}

function configuredVariables(scope: 'conversation' | 'user', variables: ChatflowVariableDefinition[] = []): ChatflowVariableItem[] {
  return variables
    .map((item): ChatflowVariableItem | null => {
      const name = String(item.name || '').trim()
      if (!name) return null
      const label = String(item.label || name).trim()
      const type = String(item.type || 'string').trim() || 'string'
      return {
        key: name,
        label,
        name,
        type,
        reference: `{{${scope}.${name}}}`,
        readonly: false,
      }
    })
    .filter((item): item is ChatflowVariableItem => item !== null)
}
