import { describe, expect, it } from 'vitest'

import { isResourceSelectable, resourceStatusLabel, type WorkflowResource } from './resourceRegistry'

describe('workflow resource registry contract', () => {
  it('renders enabled, disabled, unhealthy, and missing credential states', () => {
    const enabled: WorkflowResource = {
      resourceId: 'mcp:1:lookup_order',
      resourceType: 'MCP_TOOL',
      displayName: 'lookup_order',
      enabled: true,
      credentialStatus: 'PRESENT',
      runtimeStatus: 'READY',
      healthStatus: 'UP',
      disabledReason: '',
      inputSchema: { type: 'object' },
      outputSchema: { type: 'object' },
      capabilities: ['read'],
      flowTypeSupport: ['WORKFLOW', 'CHATFLOW'],
    }
    const disabled = { ...enabled, resourceId: 'mcp:2', enabled: false, runtimeStatus: 'DISABLED', disabledReason: 'Resource disabled by admin' } as WorkflowResource
    const unhealthy = { ...enabled, resourceId: 'mcp:3', enabled: false, healthStatus: 'DOWN', disabledReason: 'Unsupported MCP endpoint' } as WorkflowResource
    const missingCredential = { ...enabled, resourceId: 'mcp:4', enabled: false, credentialStatus: 'MISSING', disabledReason: 'Missing credential' } as WorkflowResource

    expect(resourceStatusLabel(enabled)).toBe('可用')
    expect(resourceStatusLabel(disabled)).toBe('已停用')
    expect(resourceStatusLabel(unhealthy)).toBe('不可用：Unsupported MCP endpoint')
    expect(resourceStatusLabel(missingCredential)).toBe('缺少凭证')
    expect(isResourceSelectable(enabled)).toBe(true)
    expect(isResourceSelectable(disabled)).toBe(false)
    expect(isResourceSelectable(unhealthy)).toBe(false)
    expect(isResourceSelectable(missingCredential)).toBe(false)
  })
})
