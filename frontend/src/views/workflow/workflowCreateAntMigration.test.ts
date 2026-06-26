// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function readSource(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

function regexMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern)) as RegExpMatchArray[]
}

describe('workflow create Ant migration', () => {
  it('keeps workflow/chatflow canvas off Element Plus contracts', () => {
    const file = 'src/views/workflow/WorkflowCreate.vue'
    const content = readSource(file)
    const matches = [
      ...regexMatches(content, /element-plus|@element-plus\/icons-vue/g).map((match) => `${file} -> ${match[0]}`),
      ...regexMatches(content, /<el-|<\/el-/g).map((match) => `${file} -> ${match[0]}`),
      ...regexMatches(content, /\bEl[A-Z][A-Za-z]+/g).map((match) => `${file} -> ${match[0]}`),
      ...regexMatches(content, /\.el-|--el-/g).map((match) => `${file} -> ${match[0]}`),
    ]

    expect(matches).toEqual([])
  })

  it('keeps the app entry free of the legacy route loader', () => {
    const main = readSource('src/main.ts')

    expect(main).not.toContain('legacy-element-plus')
    expect(main).not.toContain('requiresLegacyElementPlus')
    expect(main).not.toContain('installLegacyElementPlus')
  })

  it('exposes targeted test run controls for published versions', () => {
    const content = readSource('src/views/workflow/WorkflowCreate.vue')
    const versionListStart = content.indexOf('data-testid="workflow-version-list"')
    const versionListEnd = content.indexOf('</section>', versionListStart)
    const versionList = content.slice(versionListStart, versionListEnd)

    expect(versionList).toContain('data-testid="workflow-version-run"')
    expect(versionList).toContain('runPublishedVersion(version.id)')
    expect(content).toContain('targetedPublishedRunResult')
    expect(content).toContain('versionId')
  })

  it('exposes realtime version test controls and result evidence beside published-run testing', () => {
    const content = readSource('src/views/workflow/WorkflowCreate.vue')
    const versionListStart = content.indexOf('data-testid="workflow-version-list"')
    const versionListEnd = content.indexOf('</section>', versionListStart)
    const versionList = content.slice(versionListStart, versionListEnd)

    expect(versionList).toContain('data-testid="workflow-version-run"')
    expect(versionList).toContain('data-testid="workflow-version-run-v2"')
    expect(versionList).toContain('实时测试')
    expect(versionList).toContain('runPublishedVersionWithRuntimeV2(version.id)')
    expect(content).toContain('targetedRuntimeV2RunResult')
    expect(content).toContain('实时运行版本 v')
    expect(content).toContain('versionId')
    expect(versionList).not.toContain('debugRef')
  })

  it('renders the canvas title input on chatflow create entry so the placeholder is reachable', () => {
    const content = readSource('src/views/workflow/WorkflowCreate.vue')

    // The placeholder text the E2E and users rely on must still exist.
    expect(content).toContain("'Chatflow 名称'")

    // loadWorkflow's create-mode branch must enter title-editing so the placeholder input renders
    // without requiring users to click the title display button first.
    const loadStart = content.indexOf('async function loadWorkflow()')
    expect(loadStart).toBeGreaterThan(-1)
    const loadEnd = content.indexOf('\n}\n', loadStart)
    const loadBody = content.slice(loadStart, loadEnd)
    const createBranchStart = loadBody.indexOf('if (!isEditing.value)')
    expect(createBranchStart).toBeGreaterThan(-1)
    const createBranchEnd = loadBody.indexOf('return', createBranchStart)
    const createBranch = loadBody.slice(createBranchStart, createBranchEnd)
    expect(createBranch).toContain('flowTitleEditing.value = true')
  })

  it('exposes a runtime v2 cancel control in the debug dock', () => {
    const content = readSource('src/views/workflow/WorkflowCreate.vue')
    const dockStart = content.indexOf('data-testid="workflow-debug-dock"')
    const dockEnd = content.indexOf('data-testid="debug-error-panel"', dockStart)
    const debugDockHeader = content.slice(dockStart, dockEnd)

    expect(content).toContain('cancelRuntimeV2Run')
    expect(debugDockHeader).toContain('data-testid="debug-runtime-v2-cancel"')
    expect(debugDockHeader).toContain('aria-label="取消运行"')
    expect(debugDockHeader).toContain('@click="cancelCurrentRuntimeV2Run"')
  })
})
