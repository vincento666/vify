export type WorkflowModuleFlowType = 'WORKFLOW' | 'CHATFLOW'

export interface WorkflowModuleTab {
  label: string
  path: string
  flowType: WorkflowModuleFlowType
}

export const WORKFLOW_MODULE_TABS: WorkflowModuleTab[] = [
  { label: '工作流', path: '/workflows', flowType: 'WORKFLOW' },
  { label: '对话流', path: '/chatflows', flowType: 'CHATFLOW' },
]

export function getActiveWorkflowModulePath(path: string) {
  return path.startsWith('/chatflows') ? '/chatflows' : '/workflows'
}
