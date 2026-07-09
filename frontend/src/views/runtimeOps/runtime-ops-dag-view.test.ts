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
      { source: 'router', target: 'vip', state: 'selected', stateLabel: '已选择' },
      { source: 'router', target: 'fallback', state: 'skipped', stateLabel: '已跳过' },
    ])
  })

  it('projects join state and parallel wave overlap evidence', () => {
    const view = buildRuntimeOpsDagView({
      runId: 702,
      nodes: [
        {
          nodeKey: 'api_a',
          nodeType: 'API_CALL',
          status: 'COMPLETED',
          createdAt: '2026-07-09T11:00:00.000Z',
          finishedAt: '2026-07-09T11:00:00.700Z',
          selectionState: { state: 'completed', selectedUpstreamNodeKeys: ['start'], parallelWaveKey: 'wave-1' },
        },
        {
          nodeKey: 'api_b',
          nodeType: 'API_CALL',
          status: 'COMPLETED',
          createdAt: '2026-07-09T11:00:00.040Z',
          finishedAt: '2026-07-09T11:00:00.760Z',
          selectionState: { state: 'completed', selectedUpstreamNodeKeys: ['start'], parallelWaveKey: 'wave-1' },
        },
        {
          nodeKey: 'join',
          nodeType: 'END',
          status: 'WAITING',
          selectionState: {
            state: 'waiting',
            selectedUpstreamNodeKeys: ['api_a', 'api_b'],
            skippedUpstreamNodeKeys: ['audit_leaf'],
            join: {
              requiredUpstreamNodeKeys: ['api_a', 'api_b'],
              completedUpstreamNodeKeys: ['api_a'],
              skippedUpstreamNodeKeys: ['audit_leaf'],
            },
          },
        },
        {
          nodeKey: 'join_ready',
          nodeType: 'END',
          status: 'RUNNING',
          selectionState: {
            state: 'running',
            selectedUpstreamNodeKeys: ['api_a', 'api_b'],
            join: {
              requiredUpstreamNodeKeys: ['api_a', 'api_b'],
              completedUpstreamNodeKeys: ['api_a', 'api_b'],
            },
          },
        },
        {
          nodeKey: 'join_done',
          nodeType: 'END',
          status: 'COMPLETED',
          selectionState: {
            state: 'completed',
            selectedUpstreamNodeKeys: ['api_a', 'api_b'],
            join: {
              requiredUpstreamNodeKeys: ['api_a', 'api_b'],
              completedUpstreamNodeKeys: ['api_a', 'api_b'],
            },
          },
        },
      ],
    })

    expect(view.nodes.find((node) => node.nodeKey === 'join')).toMatchObject({
      joinState: 'waiting',
      joinStateLabel: '等待汇合',
      joinWaitingOnNodeKeys: ['api_b'],
    })
    expect(view.nodes.find((node) => node.nodeKey === 'join_ready')).toMatchObject({
      joinState: 'ready',
      joinStateLabel: '可汇合',
      joinWaitingOnNodeKeys: [],
    })
    expect(view.nodes.find((node) => node.nodeKey === 'join_done')).toMatchObject({
      joinState: 'completed',
      joinStateLabel: '已汇合',
      joinWaitingOnNodeKeys: [],
    })
    expect(view.edges).toContainEqual({
      source: 'audit_leaf',
      target: 'join',
      state: 'skipped',
      stateLabel: '已跳过',
    })
    expect(view.parallelWaves).toEqual([
      {
        key: 'wave-1',
        nodeKeys: ['api_a', 'api_b'],
        overlap: true,
        overlapLabel: '并行重叠',
      },
    ])
  })
})
