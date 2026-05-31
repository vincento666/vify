import { describe, expect, it } from 'vitest'

import { buildChatflowOpenShell, evaluateChatflowPublishGate } from './chatflowPublish'

describe('chatflow publish shell', () => {
  it('builds channel and Open API fields for a Chatflow resource', () => {
    const shell = buildChatflowOpenShell({ chatflowId: 12, channel: 'web' })

    expect(shell.endpoint).toBe('/api/v1/chatflows/12/runs')
    expect(shell.channelFields).toEqual([
      { label: '默认渠道', value: 'web' },
      { label: '调用方式', value: 'POST' },
      { label: '资源类型', value: 'CHATFLOW' },
    ])
  })

  it('blocks publish until a successful current conversation run exists', () => {
    expect(evaluateChatflowPublishGate({ lastRunStatus: '', dirtySinceTestRun: false }).allowed).toBe(false)
    expect(evaluateChatflowPublishGate({ lastRunStatus: 'FAILED', dirtySinceTestRun: false }).allowed).toBe(false)
    expect(evaluateChatflowPublishGate({ lastRunStatus: 'SUCCEEDED', dirtySinceTestRun: true }).allowed).toBe(false)
    expect(evaluateChatflowPublishGate({ lastRunStatus: 'SUCCEEDED', dirtySinceTestRun: false }).allowed).toBe(true)
  })
})
