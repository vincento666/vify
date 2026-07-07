import { describe, expect, it } from 'vitest'

import { buildRuntimeOpsDagView } from './runtimeOpsDag'

describe('runtime ops DAG view model', () => {
  it('projects selected, skipped, running, completed, failed, and waiting node states', () => {
    const view = buildRuntimeOpsDagView({
      runId: 701,
      nodes: [
        {
          nodeKey: 'router',
          nodeType: 'CONDITION',
          name: 'Router',
          status: 'SUCCEEDED',
          selectionState: { state: 'completed' },
        },
        {
          nodeKey: 'vip',
          nodeType: 'MESSAGE',
          name: 'VIP Reply',
          status: 'SUCCEEDED',
          selectionState: { state: 'completed', selectedUpstreamNodeKeys: ['router'] },
        },
        {
          nodeKey: 'fallback',
          nodeType: 'MESSAGE',
          name: 'Fallback',
          status: 'SKIPPED',
          selectionState: { state: 'skipped', skippedUpstreamNodeKeys: ['router'] },
        },
        {
          nodeKey: 'llm',
          nodeType: 'LLM',
          name: 'LLM Draft',
          status: 'RUNNING',
          selectionState: { state: 'running' },
        },
        {
          nodeKey: 'question',
          nodeType: 'QUESTION',
          name: 'Collect Input',
          status: 'WAITING',
          selectionState: { state: 'waiting' },
        },
        {
          nodeKey: 'api',
          nodeType: 'API_CALL',
          name: 'API Failure',
          status: 'FAILED',
          selectionState: { state: 'failed' },
          error: 'timeout',
        },
      ],
    })

    expect(view.runId).toBe(701)
    expect(view.summary).toEqual({
      completed: 2,
      skipped: 1,
      running: 1,
      waiting: 1,
      failed: 1,
    })
    expect(view.nodes.map((node) => [node.nodeKey, node.state, node.stateLabel])).toEqual([
      ['router', 'completed', '已完成'],
      ['vip', 'completed', '已完成'],
      ['fallback', 'skipped', '已跳过'],
      ['llm', 'running', '运行中'],
      ['question', 'waiting', '等待中'],
      ['api', 'failed', '已失败'],
    ])
    expect(view.edges).toEqual([
      { source: 'router', target: 'vip', state: 'selected' },
      { source: 'router', target: 'fallback', state: 'skipped' },
    ])
  })
})
