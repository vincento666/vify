export interface ChatflowRunProfile {
  message: string
  conversationId: string
  conversationName?: string
  userId: string
  channel: string
  round: number
  files?: unknown[]
}

export function buildChatflowRunInput(profile: ChatflowRunProfile): Record<string, unknown> {
  const now = new Date().toISOString()
  const messageId = `msg-${Date.now()}`
  const conversationName = profile.conversationName || profile.conversationId
  const files = profile.files || []
  const global = {
    brand: 'Hify',
    locale: 'zh-CN',
  }
  const conversation = {
    topic: conversationName,
    last_message: profile.message,
  }
  const user = {
    name: profile.userId,
    vip_level: 'standard',
  }
  const channel = {
    name: profile.channel,
    source: profile.channel,
  }
  const input = {
    payload: profile.message,
    trace_id: messageId,
  }

  return {
    userMessage: profile.message,
    USER_INPUT: profile.message,
    'sys.query': profile.message,
    'sys.conversation_id': profile.conversationId,
    'sys.conversation_name': conversationName,
    'sys.user_id': profile.userId,
    'sys.channel': profile.channel,
    'sys.now': now,
    'sys.message_id': messageId,
    'sys.round': profile.round,
    'sys.files': files,
    'global.brand': global.brand,
    'global.locale': global.locale,
    'conversation.topic': conversation.topic,
    'conversation.last_message': conversation.last_message,
    'user.name': user.name,
    'user.vip_level': user.vip_level,
    'channel.name': channel.name,
    'channel.source': channel.source,
    'input.payload': input.payload,
    'input.trace_id': input.trace_id,
    sys: {
      query: profile.message,
      conversation_id: profile.conversationId,
      conversation_name: conversationName,
      user_id: profile.userId,
      channel: profile.channel,
      now,
      message_id: messageId,
      round: profile.round,
      files,
    },
    global,
    conversation,
    user,
    channel,
    input,
  }
}
