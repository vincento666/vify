// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function readWorkflowCreateSource() {
  return readFileSync(resolve(projectRoot, 'src/views/workflow/WorkflowCreate.vue'), 'utf8')
}

describe('workflow node run status badge', () => {
  it('renders clear running/success/failure state badges on canvas nodes', () => {
    const content = readWorkflowCreateSource()

    expect(content).toContain("COMPLETED: '成功'")
    expect(content).toContain('role="status"')
    expect(content).toContain(':aria-label="`节点运行状态：${nodeProps.data.runStatusLabel}`"')
    expect(content).toContain('.node-run-status.status-succeeded .node-run-status-icon::before,')
    expect(content).toContain('.node-run-status.status-completed .node-run-status-icon::before')
    expect(content).toContain('.node-run-status.status-succeeded,\n.node-run-status.status-completed')
    expect(content).toContain('height: 1.4rem;')
    expect(content).toContain('font-size: 0.6125rem;')
    expect(content).toContain('width: 0.7rem;')
    expect(content).toContain('height: 0.7rem;')
  })

  it('hydrates workflow runtime v2 node statuses after a canvas run', () => {
    const content = readWorkflowCreateSource()

    expect(content).toContain("await loadRuntimeV2DebugDetail(lastTestRunId.value, 'WORKFLOW')")
    expect(content).toContain('await loadWorkflowRunDebugDetail(lastTestRunId.value)')
  })

  it('emphasizes the active Chatflow blocking node with reduced-motion fallback', () => {
    const content = readWorkflowCreateSource()

    expect(content).toContain("'chatflow-blocking-node': isChatflowBlockingNode(nodeProps.data.nodeKey)")
    expect(content).toContain(":data-testid=\"isChatflowBlockingNode(nodeProps.data.nodeKey) ? 'chatflow-blocking-node' : undefined\"")
    expect(content).toContain('.coze-node.chatflow-blocking-node::before')
    expect(content).toContain('@keyframes chatflow-blocking-border-flow')
    expect(content).toContain('@media (prefers-reduced-motion: reduce)')
  })
})
