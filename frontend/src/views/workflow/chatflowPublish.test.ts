import { describe, expect, it } from 'vitest'

import {
  buildChatflowChannelRows,
  buildChatflowOpenShell,
  buildWorkflowVersionRows,
  evaluateChatflowPublishGate,
} from './chatflowPublish'

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

  it('formats runnable and disabled channel shells for the Open API panel', () => {
    const rows = buildChatflowChannelRows([
      {
        channelId: 'api',
        displayName: 'REST API',
        enabled: true,
        runnable: true,
        unavailableReason: '',
        deliveryCapabilities: { sync: true, streaming: true, files: true, cards: false },
        normalizedInputFields: ['sys.query', 'sys.channel', 'channel.metadata'],
        configSchema: { type: 'object' },
      },
      { channelId: 'web', displayName: 'Web Chat', enabled: true, runnable: true, unavailableReason: '', deliveryCapabilities: { sync: true } },
      { channelId: 'feishu', displayName: 'Feishu', enabled: false, runnable: false, unavailableReason: '缺少 webhook 验签和凭据配置', deliveryCapabilities: { sync: false, streaming: false, files: false, cards: false } },
    ])

    expect(rows).toEqual([
      {
        id: 'api',
        name: 'REST API',
        status: '可运行',
        disabled: false,
        reason: '',
        capabilities: '同步 / 流式 / 文件',
        normalizedInputFields: ['sys.query', 'sys.channel', 'channel.metadata'],
        hasConfigSchema: true,
      },
      {
        id: 'web',
        name: 'Web Chat',
        status: '可运行',
        disabled: false,
        reason: '',
        capabilities: '同步',
        normalizedInputFields: [],
        hasConfigSchema: false,
      },
      {
        id: 'feishu',
        name: 'Feishu',
        status: '未启用',
        disabled: true,
        reason: '缺少 webhook 验签和凭据配置',
        capabilities: '不可投递',
        normalizedInputFields: [],
        hasConfigSchema: false,
      },
    ])
  })

  it('formats published versions with active rollback state', () => {
    const rows = buildWorkflowVersionRows([
      { id: 9, version: 2, active: true, createdAt: '2026-06-03T01:00:00' },
      { id: 3, version: 1, active: false, createdAt: '2026-06-03T00:00:00' },
    ])

    expect(rows).toEqual([
      { id: 9, label: 'v2', status: '当前版本', canRollback: false, createdAt: '2026-06-03T01:00:00' },
      { id: 3, label: 'v1', status: '可回滚', canRollback: true, createdAt: '2026-06-03T00:00:00' },
    ])
  })
})
