import { createRouter, createWebHistory } from 'vue-router'

import { WORKFLOW_MODULE_TABS } from '@/views/workflow/workflowModuleTabs'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: { name: 'HifyProvider' },
    },
    {
      path: '/provider',
      name: 'HifyProvider',
      component: () => import('@/views/provider/ProviderList.vue'),
    },
    {
      path: '/agent',
      name: 'HifyAgent',
      component: () => import('@/views/agent/AgentList.vue'),
    },
    {
      path: '/agents/new',
      name: 'HifyAgentNew',
      meta: { agentWorkbench: true },
      component: () => import('@/views/agent/AgentWorkbench.vue'),
    },
    {
      path: '/agents/:id/workbench',
      name: 'HifyAgentWorkbench',
      meta: { agentWorkbench: true },
      component: () => import('@/views/agent/AgentWorkbench.vue'),
    },
    {
      path: '/chat',
      name: 'HifyChat',
      component: () => import('@/views/chat/ChatView.vue'),
    },
    {
      path: '/runtime-lab/chat',
      name: 'HifyRuntimeLabChat',
      meta: { runtimeLabChat: true },
      component: () => import('@/views/chat/UnifiedRoutingChatLab.vue'),
    },
    {
      path: '/customer-assistant',
      name: 'HifyCustomerAssistant',
      meta: { customerAssistant: true },
      component: () => import('@/views/customerAssistant/CustomerAssistantPanel.vue'),
    },
    {
      path: '/ai-assistant',
      name: 'HifyAiAssistant',
      meta: { aiAssistant: true },
      component: () => import('@/views/aiAssistant/AiAssistantShell.vue'),
    },
    {
      path: '/knowledge',
      name: 'HifyKnowledge',
      component: () => import('@/views/knowledge/KnowledgeList.vue'),
    },
    {
      path: '/knowledge/:kbId/documents',
      name: 'HifyKnowledgeDocuments',
      component: () => import('@/views/knowledge/DocumentList.vue'),
    },
    {
      path: '/workflows',
      name: 'HifyWorkflows',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS },
      component: () => import('@/views/workflow/WorkflowList.vue'),
    },
    {
      path: '/workflows/create',
      name: 'HifyWorkflowsCreate',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS, canvasWorkbench: true },
      component: () => import('@/views/workflow/WorkflowCreate.vue'),
    },
    {
      path: '/workflows/:id/canvas',
      name: 'HifyWorkflowsCanvas',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS, canvasWorkbench: true },
      component: () => import('@/views/workflow/WorkflowCreate.vue'),
    },
    {
      path: '/workflow/api-resources',
      name: 'HifyWorkflowsApiResources',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS },
      component: () => import('@/views/workflow/ApiResourceWorkbench.vue'),
    },
    {
      path: '/chatflows',
      name: 'HifyChatflows',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS },
      component: () => import('@/views/workflow/ChatflowList.vue'),
    },
    {
      path: '/chatflows/create',
      name: 'HifyChatflowsCreate',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS, canvasWorkbench: true },
      component: () => import('@/views/workflow/WorkflowCreate.vue'),
    },
    {
      path: '/chatflows/:id/canvas',
      name: 'HifyChatflowsCanvas',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS, canvasWorkbench: true },
      component: () => import('@/views/workflow/WorkflowCreate.vue'),
    },
    {
      path: '/evaluation',
      name: 'HifyEvaluation',
      meta: { defaultEvaluationTab: 'experiments' },
      component: () => import('@/views/evaluation/EvaluationWorkbench.vue'),
    },
    {
      path: '/evaluation/eval-sets/:id',
      name: 'HifyEvaluationEvalSets',
      meta: { defaultEvaluationTab: 'eval-sets', hideShellBreadcrumb: true },
      component: () => import('@/views/evaluation/EvalSetDetail.vue'),
    },
    {
      path: '/observe',
      name: 'HifyObserve',
      component: () => import('@/views/workflow/ObserveRedirect.vue'),
    },
    {
      path: '/mcp',
      name: 'HifyMcp',
      component: () => import('@/views/mcp/McpServerList.vue'),
    },
    {
      path: '/mcp/:id/debug',
      name: 'HifyMcpDebug',
      component: () => import('@/views/mcp/McpServerDebug.vue'),
    },
  ],
})

export default router
