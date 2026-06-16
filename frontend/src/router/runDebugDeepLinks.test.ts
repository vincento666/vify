import { describe, expect, it } from 'vitest'

import {
  buildAgentPreviewDebugLink,
  buildChatflowRunDebugLink,
  buildWorkflowRunDebugLink,
} from './runDebugDeepLinks'

describe('composer run debug deep links', () => {
  it('builds workflow canvas links for concrete run and execute identifiers', () => {
    expect(buildWorkflowRunDebugLink(12, { runId: 34 })).toEqual({
      name: 'HifyWorkflowsCanvas',
      params: { id: 12 },
      query: { runId: '34', debug: '1' },
    })
    expect(buildWorkflowRunDebugLink(12, { executeId: 'exec-88' })).toEqual({
      name: 'HifyWorkflowsCanvas',
      params: { id: 12 },
      query: { executeId: 'exec-88', debug: '1' },
    })
  })

  it('builds chatflow canvas links for concrete run and execute identifiers', () => {
    expect(buildChatflowRunDebugLink(21, { runId: 55 })).toEqual({
      name: 'HifyChatflowsCanvas',
      params: { id: 21 },
      query: { runId: '55', debug: '1' },
    })
    expect(buildChatflowRunDebugLink(21, { executeId: 'exec-chat' })).toEqual({
      name: 'HifyChatflowsCanvas',
      params: { id: 21 },
      query: { executeId: 'exec-chat', debug: '1' },
    })
  })

  it('builds agent workbench links for preview runs', () => {
    expect(buildAgentPreviewDebugLink(7, 99)).toEqual({
      name: 'HifyAgentWorkbench',
      params: { id: 7 },
      query: { previewRunId: '99', debug: '1' },
    })
  })
})
