import { describe, expect, it } from 'vitest'

import {
  buildChatflowRunCallTree,
  buildChatflowRunFlamegraph,
  projectRuntimeV2ChatflowSessionState,
  summarizeChatflowRunDebug,
  withChatflowSessionState,
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

  it('projects runtime v2 interrupted checkpoints as waiting chatflow session state', () => {
    const session = projectRuntimeV2ChatflowSessionState(
      {
        runId: 88,
        status: 'INTERRUPTED',
        checkpoint: {
          id: 5,
          eventId: 80,
          pendingNodeKey: 'question_1',
          resumeSchema: { nodeKey: 'question_1', question: '主题？', answerType: 'text' },
          status: 'waiting',
        },
      },
      'INTERRUPTED',
      { sessionId: 'conv-demo', conversationId: 'conv-demo', userId: 'user-demo', channel: 'web' },
    )

    expect(session).toMatchObject({
      sessionId: 'conv-demo',
      conversationId: 'conv-demo',
      userId: 'user-demo',
      channel: 'web',
      status: 'waiting',
      currentRunId: 88,
      checkpoint: {
        pendingNodeKey: 'question_1',
        eventId: 80,
      },
    })

    expect(withChatflowSessionState({ runId: 88, status: 'INTERRUPTED', nodeDetails: [] }, session)).toMatchObject({
      session,
      checkpoint: session.checkpoint,
      variables: {},
    })
  })

  it('keeps runtime v2 variable snapshots in chatflow session debug state', () => {
    const session = projectRuntimeV2ChatflowSessionState(
      {
        runId: 91,
        sessionId: 'session-91',
        conversationId: 'conv-91',
        userId: 'user-91',
        channel: 'web',
        status: 'WAITING',
        variables: {
          conversation: { topic: 'refund' },
          sys: { query: 'order status' },
        },
        waitingEvent: {
          id: 15,
          nodeKey: 'human_input_1',
          checkpointId: 7,
        },
      },
      'WAITING',
    )

    expect(session).toMatchObject({
      sessionId: 'session-91',
      conversationId: 'conv-91',
      userId: 'user-91',
      channel: 'web',
      status: 'waiting',
      currentRunId: 91,
      variables: {
        conversation: { topic: 'refund' },
        sys: { query: 'order status' },
      },
      waitingEvent: {
        id: 15,
        nodeKey: 'human_input_1',
        checkpointId: 7,
      },
    })
  })

  it('clears stale runtime v2 waiting state when a chatflow run reaches terminal status', () => {
    const session = projectRuntimeV2ChatflowSessionState(
      {
        runId: 91,
        sessionId: 'session-91',
        status: 'SUCCEEDED',
        variables: {
          conversation: { topic: 'refund' },
        },
      },
      'SUCCEEDED',
      {
        sessionId: 'session-91',
        conversationId: 'conv-91',
        userId: 'user-91',
        channel: 'web',
        status: 'waiting',
        checkpoint: { id: 7, pendingNodeKey: 'question_1' },
        waitingEvent: { id: 15, nodeKey: 'question_1' },
      },
    )

    expect(session).toMatchObject({
      status: 'completed',
      checkpoint: null,
      waitingEvent: null,
      variables: {
        conversation: { topic: 'refund' },
      },
    })
  })
})
