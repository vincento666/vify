export type WorkflowResourceType = 'MCP_TOOL' | 'INTERNAL_TOOL' | 'API_TOOL' | 'SUBWORKFLOW' | 'KNOWLEDGE_BASE' | string
export type ResourceCredentialStatus = 'PRESENT' | 'MISSING' | 'NOT_REQUIRED' | string
export type ResourceRuntimeStatus = 'READY' | 'DISABLED' | 'UNHEALTHY' | 'CREDENTIAL_MISSING' | 'NOT_PUBLISHED' | 'SCHEMA_MISSING' | string
export type ResourceHealthStatus = 'UP' | 'DOWN' | 'UNKNOWN' | string

export interface WorkflowResource {
  resourceId: string
  resourceType: WorkflowResourceType
  displayName: string
  description?: string
  enabled: boolean
  inputSchema: Record<string, unknown>
  outputSchema: Record<string, unknown>
  capabilities: string[]
  flowTypeSupport: string[]
  credentialStatus: ResourceCredentialStatus
  runtimeStatus: ResourceRuntimeStatus
  healthStatus: ResourceHealthStatus
  disabledReason: string
  metadata?: Record<string, unknown>
}

export function isResourceSelectable(resource: WorkflowResource) {
  return resource.enabled
    && resource.credentialStatus !== 'MISSING'
    && resource.healthStatus !== 'DOWN'
    && resource.runtimeStatus === 'READY'
}

export function resourceStatusLabel(resource: WorkflowResource) {
  if (isResourceSelectable(resource)) return '可用'
  if (resource.credentialStatus === 'MISSING') return '缺少凭证'
  if (resource.runtimeStatus === 'DISABLED') return '已停用'
  if (resource.disabledReason) return `不可用：${resource.disabledReason}`
  if (resource.healthStatus === 'DOWN') return '不可用：健康检查失败'
  return '不可用'
}
