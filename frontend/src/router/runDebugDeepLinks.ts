type RunDebugIdentity =
  | { runId: number | string; executeId?: never }
  | { executeId: number | string; runId?: never }

function queryFor(identity: RunDebugIdentity): string {
  if ('runId' in identity) {
    return `runId=${encodeURIComponent(String(identity.runId))}&debug=1`
  }
  return `executeId=${encodeURIComponent(String(identity.executeId))}&debug=1`
}

export function buildWorkflowRunDebugLink(workflowId: number | string, identity: RunDebugIdentity): string {
  return `/workflows/${encodeURIComponent(String(workflowId))}/canvas?${queryFor(identity)}`
}

export function buildChatflowRunDebugLink(chatflowId: number | string, identity: RunDebugIdentity): string {
  return `/chatflows/${encodeURIComponent(String(chatflowId))}/canvas?${queryFor(identity)}`
}

export function buildAgentPreviewDebugLink(agentId: number | string, previewRunId: number | string): string {
  return `/agents/${encodeURIComponent(String(agentId))}/workbench?previewRunId=${encodeURIComponent(String(previewRunId))}&debug=1`
}
