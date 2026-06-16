export type WorkflowModuleFlowType = 'WORKFLOW' | 'CHATFLOW'

export interface WorkflowModuleTab {
  label: string
  path: string
  name: string
  flowType: WorkflowModuleFlowType
}

export const WORKFLOW_MODULE_TABS: WorkflowModuleTab[] = [
  { label: '工作流', path: '/workflows', name: 'HifyWorkflows', flowType: 'WORKFLOW' },
  { label: '对话流', path: '/chatflows', name: 'HifyChatflows', flowType: 'CHATFLOW' },
]

export function getActiveWorkflowModulePath(path: string) {
  return path.startsWith('/chatflows') ? '/chatflows' : '/workflows'
}
