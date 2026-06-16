import { describe, expect, it } from 'vitest'

import { buildObserveComposerRedirect } from './observeRedirect'

describe('observe compatibility redirect', () => {
  it('routes workflow runs back to the owning workflow canvas debug panel', () => {
    expect(buildObserveComposerRedirect({
      runId: 42,
      detail: { flowType: 'WORKFLOW', workflowId: 7 },
    })).toEqual({
      name: 'HifyWorkflowsCanvas',
      params: { id: 7 },
      query: { runId: '42', debug: '1' },
    })
  })

  it('routes chatflow runs back to the owning chatflow canvas debug panel', () => {
    expect(buildObserveComposerRedirect({
      runId: 84,
      detail: { flowType: 'CHATFLOW', workflowId: 9 },
    })).toEqual({
      name: 'HifyChatflowsCanvas',
      params: { id: 9 },
      query: { runId: '84', debug: '1' },
    })
  })

  it('falls back to the composer list when the run cannot be resolved', () => {
    expect(buildObserveComposerRedirect({
      runId: 0,
      detail: null,
    })).toEqual({ name: 'HifyWorkflows' })
  })
})
