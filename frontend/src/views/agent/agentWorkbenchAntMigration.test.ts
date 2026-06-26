// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

function regexMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern)) as RegExpMatchArray[]
}

describe('Agent workbench Ant Design Vue migration', () => {
  it('keeps AgentWorkbench off Element Plus contracts', () => {
    const content = readProjectFile('src/views/agent/AgentWorkbench.vue')
    const matches = [
      ...regexMatches(content, /element-plus|@element-plus\/icons-vue/g).map((match) => match[0]),
      ...regexMatches(content, /<el-/g).map((match) => match[0]),
      ...regexMatches(content, /\.el-|--el-/g).map((match) => match[0]),
    ]

    expect(matches).toEqual([])
  })

  it('keeps MCP, knowledge base and workflow capability selects discoverable by the capabilities e2e', () => {
    // The e2e contract (frontend/e2e/agent-workbench-capabilities.mjs:29-42) clicks
    // `.capability-card .el-select` to open the dropdown and locates options with
    // `.el-select-dropdown__item` filtered by name. After the Ant Design migration
    // those legacy Element Plus selectors disappeared, leaving the e2e unable to
    // pick MCP / KB / Workflow options. Each capability select must retain a
    // compat marker class so the existing e2e locator still resolves to the
    // rendered Ant option/control.
    const content = readProjectFile('src/views/agent/AgentWorkbench.vue')

    // KB select trigger compat marker
    const kbSelectStart = content.indexOf('v-model:value="form.knowledgeBaseIds"')
    expect(kbSelectStart).toBeGreaterThan(-1)
    const kbSelectOpenTag = content.slice(content.lastIndexOf('<a-select', kbSelectStart), kbSelectStart + 200)
    expect(kbSelectOpenTag).toMatch(/class="[^"]*\bel-select\b[^"]*"/)

    // Workflow select trigger compat marker
    const wfSelectStart = content.indexOf('v-model:value="form.workflowId"')
    expect(wfSelectStart).toBeGreaterThan(-1)
    const wfSelectOpenTag = content.slice(content.lastIndexOf('<a-select', wfSelectStart), wfSelectStart + 200)
    expect(wfSelectOpenTag).toMatch(/class="[^"]*\bel-select\b[^"]*"/)

    // MCP option compat marker (e2e filters `.el-select-dropdown__item` by MCP name)
    const mcpSelectStart = content.indexOf('data-testid="agent-mcp-tool-select"')
    expect(mcpSelectStart).toBeGreaterThan(-1)
    const mcpSelectBlockEnd = content.indexOf('</a-select>', mcpSelectStart)
    expect(mcpSelectBlockEnd).toBeGreaterThan(mcpSelectStart)
    const mcpSelectBlock = content.slice(mcpSelectStart, mcpSelectBlockEnd)
    expect(mcpSelectBlock).toMatch(/class="[^"]*\bel-select-dropdown__item\b[^"]*"/)

    // KB option compat marker
    const kbBlockEnd = content.indexOf('</a-select>', kbSelectStart)
    expect(kbBlockEnd).toBeGreaterThan(kbSelectStart)
    const kbBlock = content.slice(kbSelectStart, kbBlockEnd)
    expect(kbBlock).toMatch(/class="[^"]*\bel-select-dropdown__item\b[^"]*"/)

    // Workflow option compat marker
    const wfBlockEnd = content.indexOf('</a-select>', wfSelectStart)
    expect(wfBlockEnd).toBeGreaterThan(wfSelectStart)
    const wfBlock = content.slice(wfSelectStart, wfBlockEnd)
    expect(wfBlock).toMatch(/class="[^"]*\bel-select-dropdown__item\b[^"]*"/)
  })

  it('pins retrieval-settings panel labels to the workbench retrieval e2e contract', () => {
    // The e2e (frontend/e2e/agent-workbench-retrieval-settings.mjs:73-78) reads
    // the `agent-retrieval-settings` panel and asserts the visible labels
    // "Top K", "Score 阈值" and "引用格式" are rendered. Those labels must
    // remain in the retrieval settings panel so the contract holds after Ant
    // Design migration renames.
    const content = readProjectFile('src/views/agent/AgentWorkbench.vue')
    const panelStart = content.indexOf('data-testid="agent-retrieval-settings"')
    expect(panelStart).toBeGreaterThan(-1)
    const panelEnd = content.indexOf('</div>', panelStart)
    expect(panelEnd).toBeGreaterThan(panelStart)
    const panelBlock = content.slice(panelStart, panelEnd)
    expect(panelBlock).toContain('<span>Top K</span>')
    expect(panelBlock).toContain('<span>Score 阈值</span>')
    expect(panelBlock).toContain('<span>引用格式</span>')
  })
})
