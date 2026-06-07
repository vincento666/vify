import { describe, expect, it } from 'vitest'

import {
  buildChatflowRunCallTree,
  buildChatflowRunFlamegraph,
  summarizeChatflowRunDebug,
} from './chatflowRunDebug'

describe('chatflow run debug view model', () => {
  const detail = {
    runId: 77,
    ownerType: 'CHATFLOW',
    status: 'SUCCEEDED',
    elapsedMs: 41,
    session: {
      sessionId: 'session-1',
      conversationId: 'conv-1',
      userId: 'user-1',
      channel: 'web',
      status: 'completed',
    },
    nodeDetails: [
      { nodeKey: 'start', nodeType: 'START', status: 'SUCCEEDED', elapsedMs: 4, outputs: { 'sys.query': 'hi' } },
      { nodeKey: 'question_1', nodeType: 'QUESTION', status: 'SUCCEEDED', elapsedMs: 20, outputs: { answer: 'yes' } },
      { nodeKey: 'end', nodeType: 'END', status: 'SUCCEEDED', elapsedMs: 17, outputs: { final: 'answer=yes' } },
    ],
  }

  it('summarizes session identity for the chatflow debug dock', () => {
    expect(summarizeChatflowRunDebug(detail)).toEqual({
      runLabel: 'Run #77',
      statusLabel: 'SUCCEEDED',
      sessionLabel: 'conv-1 · user-1 · web',
      nodeCountLabel: '3 nodes',
    })
  })

  it('keeps chatflow node call tree order', () => {
    expect(buildChatflowRunCallTree(detail).map((node) => node.nodeKey)).toEqual(['question_1'])
  })

  it('builds chatflow flamegraph rows from cumulative elapsed time', () => {
    expect(buildChatflowRunFlamegraph(detail).map((row) => `${row.nodeKey}:${row.startMs}:${row.durationMs}`)).toEqual([
      'question_1:0:20',
    ])
  })
})
