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
  }
}
