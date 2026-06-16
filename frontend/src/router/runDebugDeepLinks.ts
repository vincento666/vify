import type { RouteLocationRaw } from 'vue-router'

type RunDebugIdentity =
  | { runId: number | string; executeId?: never }
  | { executeId: number | string; runId?: never }

function queryFor(identity: RunDebugIdentity): Record<string, string> {
  if ('runId' in identity) {
    return { runId: String(identity.runId), debug: '1' }
  }
  return { executeId: String(identity.executeId), debug: '1' }
}

export function buildWorkflowRunDebugLink(workflowId: number | string, identity: RunDebugIdentity): RouteLocationRaw {
  return { name: 'HifyWorkflowsCanvas', params: { id: workflowId }, query: queryFor(identity) }
}

export function buildChatflowRunDebugLink(chatflowId: number | string, identity: RunDebugIdentity): RouteLocationRaw {
  return { name: 'HifyChatflowsCanvas', params: { id: chatflowId }, query: queryFor(identity) }
}

export function buildAgentPreviewDebugLink(agentId: number | string, previewRunId: number | string): RouteLocationRaw {
  return { name: 'HifyAgentWorkbench', params: { id: agentId }, query: { previewRunId: String(previewRunId), debug: '1' } }
}
