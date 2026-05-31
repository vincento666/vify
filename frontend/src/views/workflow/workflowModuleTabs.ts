export type WorkflowModuleFlowType = 'WORKFLOW' | 'CHATFLOW'

export interface WorkflowModuleTab {
  label: string
  path: string
  flowType: WorkflowModuleFlowType
}

export const WORKFLOW_MODULE_TABS: WorkflowModuleTab[] = [
  { label: 'Workflow', path: '/workflows', flowType: 'WORKFLOW' },
  { label: 'Chatflow', path: '/chatflows', flowType: 'CHATFLOW' },
]

export function getActiveWorkflowModulePath(path: string) {
  return path.startsWith('/chatflows') ? '/chatflows' : '/workflows'
}
