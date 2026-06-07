import { describe, expect, it } from 'vitest'

import {
  buildAgentPreviewDebugLink,
  buildChatflowRunDebugLink,
  buildWorkflowRunDebugLink,
} from './runDebugDeepLinks'

describe('composer run debug deep links', () => {
  it('builds workflow canvas links for concrete run and execute identifiers', () => {
    expect(buildWorkflowRunDebugLink(12, { runId: 34 })).toBe('/workflows/12/canvas?runId=34&debug=1')
    expect(buildWorkflowRunDebugLink(12, { executeId: 'exec-88' })).toBe('/workflows/12/canvas?executeId=exec-88&debug=1')
  })

  it('builds chatflow canvas links for concrete run and execute identifiers', () => {
    expect(buildChatflowRunDebugLink(21, { runId: 55 })).toBe('/chatflows/21/canvas?runId=55&debug=1')
    expect(buildChatflowRunDebugLink(21, { executeId: 'exec-chat' })).toBe('/chatflows/21/canvas?executeId=exec-chat&debug=1')
  })

  it('builds agent workbench links for preview runs', () => {
    expect(buildAgentPreviewDebugLink(7, 99)).toBe('/agents/7/workbench?previewRunId=99&debug=1')
  })
})
