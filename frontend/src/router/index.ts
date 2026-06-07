import { createRouter, createWebHistory } from 'vue-router'

import { WORKFLOW_MODULE_TABS } from '@/views/workflow/workflowModuleTabs'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/provider',
    },
    {
      path: '/provider',
      component: () => import('@/views/provider/ProviderList.vue'),
    },
    {
      path: '/agent',
      component: () => import('@/views/agent/AgentList.vue'),
    },
    {
      path: '/chat',
      component: () => import('@/views/chat/ChatView.vue'),
    },
    {
      path: '/runtime-lab/chat',
      meta: { runtimeLabChat: true },
      component: () => import('@/views/chat/UnifiedRoutingChatLab.vue'),
    },
    {
      path: '/knowledge',
      component: () => import('@/views/knowledge/KnowledgeList.vue'),
    },
    {
      path: '/knowledge/:kbId/documents',
      component: () => import('@/views/knowledge/DocumentList.vue'),
    },
    {
      path: '/workflows',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS },
      component: () => import('@/views/workflow/WorkflowList.vue'),
    },
    {
      path: '/workflows/create',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS, canvasWorkbench: true },
      component: () => import('@/views/workflow/WorkflowCreate.vue'),
    },
    {
      path: '/workflows/:id/canvas',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS, canvasWorkbench: true },
      component: () => import('@/views/workflow/WorkflowCreate.vue'),
    },
    {
      path: '/chatflows',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS },
      component: () => import('@/views/workflow/ChatflowList.vue'),
    },
    {
      path: '/chatflows/create',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS, canvasWorkbench: true },
      component: () => import('@/views/workflow/WorkflowCreate.vue'),
    },
    {
      path: '/chatflows/:id/canvas',
      meta: { workflowModuleTabs: WORKFLOW_MODULE_TABS, canvasWorkbench: true },
      component: () => import('@/views/workflow/WorkflowCreate.vue'),
    },
    {
      path: '/evaluation',
      meta: { defaultEvaluationTab: 'experiments' },
      component: () => import('@/views/evaluation/EvaluationWorkbench.vue'),
    },
    {
      path: '/mcp',
      component: () => import('@/views/mcp/McpServerList.vue'),
    },
    {
      path: '/mcp/:id/debug',
      component: () => import('@/views/mcp/McpServerDebug.vue'),
    },
  ],
})

export default router
