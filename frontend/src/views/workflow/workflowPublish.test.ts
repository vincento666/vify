import { describe, expect, it } from 'vitest'

import { evaluateWorkflowPublishGate } from './workflowPublish'

describe('evaluateWorkflowPublishGate', () => {
  it('blocks publish when canvas validation fails', () => {
    const gate = evaluateWorkflowPublishGate({
      validationErrors: ['START must connect to END through at least one path'],
      lastTestRunStatus: 'SUCCEEDED',
      dirtySinceTestRun: false,
    })

    expect(gate.allowed).toBe(false)
    expect(gate.reasons).toContain('画布校验未通过')
  })

  it('blocks publish before a successful test run', () => {
    const gate = evaluateWorkflowPublishGate({
      validationErrors: [],
      lastTestRunStatus: '',
      dirtySinceTestRun: false,
    })

    expect(gate.allowed).toBe(false)
    expect(gate.reasons).toContain('需要先完成一次成功试运行')
  })

  it('blocks publish when the graph changed after the last test run', () => {
    const gate = evaluateWorkflowPublishGate({
      validationErrors: [],
      lastTestRunStatus: 'SUCCEEDED',
      dirtySinceTestRun: true,
    })

    expect(gate.allowed).toBe(false)
    expect(gate.reasons).toContain('画布已变更，需要重新试运行')
  })

  it('allows publish only after valid canvas and successful current test run', () => {
    const gate = evaluateWorkflowPublishGate({
      validationErrors: [],
      lastTestRunStatus: 'SUCCEEDED',
      dirtySinceTestRun: false,
    })

    expect(gate.allowed).toBe(true)
    expect(gate.reasons).toEqual([])
  })
})
