import { describe, expect, it } from 'vitest'

import { deriveRunPathEdgeClasses } from './runPathEdges'

describe('workflow running path edge state', () => {
  it('marks the incoming edge of a running node', () => {
    const classes = deriveRunPathEdgeClasses(
      [
        { id: 'start->llm_1', sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
        { id: 'llm_1->end', sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
      ],
      [
        { nodeKey: 'start', status: 'SUCCEEDED', outputs: { USER_INPUT: 'hello' } },
        { nodeKey: 'llm_1', status: 'RUNNING', outputs: {} },
      ],
    )

    expect(classes.get('start->llm_1')).toEqual(expect.arrayContaining(['edge-running']))
    expect(classes.get('llm_1->end') || []).not.toContain('edge-running')
  })

  it('marks completed incoming edges as succeeded', () => {
    const classes = deriveRunPathEdgeClasses(
      [
        { id: 'start->llm_1', sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
        { id: 'llm_1->end', sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
      ],
      [
        { nodeKey: 'start', status: 'SUCCEEDED', outputs: { USER_INPUT: 'hello' } },
        { nodeKey: 'llm_1', status: 'SUCCEEDED', outputs: { answer: 'ok' } },
      ],
    )

    expect(classes.get('start->llm_1')).toEqual(expect.arrayContaining(['edge-succeeded']))
  })

  it('keeps the incoming edge animated while a chatflow node waits for user input', () => {
    const classes = deriveRunPathEdgeClasses(
      [
        { id: 'start->question_1', sourceNodeKey: 'start', targetNodeKey: 'question_1', condition: null },
        { id: 'question_1->end', sourceNodeKey: 'question_1', targetNodeKey: 'end', condition: null },
      ],
      [
        { nodeKey: 'start', status: 'SUCCEEDED', outputs: { 'sys.query': 'hello' } },
        { nodeKey: 'question_1', status: 'INTERRUPTED', outputs: {} },
      ],
    )

    expect(classes.get('start->question_1')).toEqual(expect.arrayContaining(['edge-running']))
  })

  it('highlights only the active condition branch and dims siblings', () => {
    const classes = deriveRunPathEdgeClasses(
      [
        { id: 'start->router', sourceNodeKey: 'start', targetNodeKey: 'router', condition: null },
        { id: 'router->vip', sourceNodeKey: 'router', targetNodeKey: 'vip', condition: 'vip' },
        { id: 'router->fallback', sourceNodeKey: 'router', targetNodeKey: 'fallback', condition: null },
      ],
      [
        { nodeKey: 'start', status: 'SUCCEEDED', outputs: { USER_INPUT: 'vip user' } },
        { nodeKey: 'router', status: 'SUCCEEDED', outputs: { route: 'vip' } },
        { nodeKey: 'vip', status: 'RUNNING', outputs: {} },
      ],
    )

    expect(classes.get('router->vip')).toEqual(expect.arrayContaining(['edge-active-branch', 'edge-running']))
    expect(classes.get('router->fallback')).toEqual(expect.arrayContaining(['edge-inactive-branch']))
    expect(classes.get('router->fallback') || []).not.toContain('edge-running')
  })

  it('uses runtime v2 selection state to dim skipped join upstreams', () => {
    const classes = deriveRunPathEdgeClasses(
      [
        { id: 'vip->end', sourceNodeKey: 'vip', targetNodeKey: 'end', condition: null },
        { id: 'fallback->end', sourceNodeKey: 'fallback', targetNodeKey: 'end', condition: null },
      ],
      [
        { nodeKey: 'vip', status: 'COMPLETED', outputs: { answer: 'vip' } },
        {
          nodeKey: 'end',
          status: 'COMPLETED',
          outputs: { final: 'vip' },
          selectionState: {
            selectedUpstreamNodeKeys: ['vip'],
            skippedUpstreamNodeKeys: ['fallback'],
          },
        },
      ],
    )

    expect(classes.get('vip->end')).toEqual(expect.arrayContaining(['edge-active-branch', 'edge-succeeded']))
    expect(classes.get('fallback->end')).toEqual(expect.arrayContaining(['edge-inactive-branch']))
    expect(classes.get('fallback->end') || []).not.toContain('edge-succeeded')
  })
})
