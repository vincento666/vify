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

function extractSelectorBlock(content: string, selector: string) {
  const start = content.indexOf(`${selector} {`)
  if (start < 0) return ''

  let depth = 0
  let blockStart = -1
  for (let index = start; index < content.length; index += 1) {
    const char = content[index]
    if (char === '{') {
      depth += 1
      if (blockStart < 0) blockStart = index + 1
      continue
    }
    if (char === '}') {
      depth -= 1
      if (depth === 0 && blockStart >= 0) {
        return content.slice(blockStart, index)
      }
    }
  }

  return ''
}

describe('workflow canvas responsive progressive collapse contract', () => {
  it('keeps the right-side config surfaces edge-anchored before the off-canvas phase', () => {
    const content = readWorkflowCreateSource()
    const configPanel = extractSelectorBlock(content, '.workflow-canvas-page.canvas-layout-right-anchored .node-config-panel')
    const runPanel = extractSelectorBlock(content, '.workflow-canvas-page.canvas-layout-right-anchored .test-run-panel')
    const opsPanel = extractSelectorBlock(content, '.workflow-canvas-page.canvas-layout-right-anchored .ops-panel')

    expect(configPanel).toContain('right: var(--debug-dock-gap);')
    expect(runPanel).toContain('right: var(--debug-dock-gap);')
    expect(opsPanel).toContain('right: var(--debug-dock-gap);')
  })

  it('shelves the right-side config surfaces before collapsing the left rail on narrow viewports', () => {
    const content = readWorkflowCreateSource()
    const configPanel = extractSelectorBlock(content, '.workflow-canvas-page.canvas-layout-right-shelved .node-config-panel')
    const runPanel = extractSelectorBlock(content, '.workflow-canvas-page.canvas-layout-right-shelved .test-run-panel')
    const opsPanel = extractSelectorBlock(content, '.workflow-canvas-page.canvas-layout-right-shelved .ops-panel')

    expect(configPanel).toContain('right: calc(-1 * (var(--workflow-side-panel-width) - var(--workflow-panel-peek-width)))')
    expect(runPanel).toContain('right: calc(-1 * (var(--workflow-side-panel-width) - var(--workflow-panel-peek-width)))')
    expect(opsPanel).toContain('right: calc(-1 * (var(--workflow-side-panel-width) - var(--workflow-panel-peek-width)))')
  })

  it('switches the center stage into an overflow-clipped overlay layer instead of squeezing every panel', () => {
    const content = readWorkflowCreateSource()
    const workbenchBlock = extractSelectorBlock(content, '.workflow-canvas-page.canvas-layout-stage-shelved .canvas-workbench')
    const stageBlock = extractSelectorBlock(content, '.workflow-canvas-page.canvas-layout-stage-shelved .canvas-stage-shell')

    expect(workbenchBlock).toContain('grid-template-columns: var(--workflow-resource-panel-width) var(--workflow-stage-min-width);')
    expect(stageBlock).toContain('min-width: var(--workflow-stage-min-width);')
    expect(stageBlock).toContain('overflow: hidden;')
  })

  it('anchors shelved right panels to the viewport once the center stage is clipped', () => {
    const content = readWorkflowCreateSource()
    const stageAndRailPanelBlock = extractSelectorBlock(
      content,
      '.workflow-canvas-page.canvas-layout-stage-shelved .node-config-panel,\n.workflow-canvas-page.canvas-layout-stage-shelved .test-run-panel,\n.workflow-canvas-page.canvas-layout-stage-shelved .ops-panel,\n.workflow-canvas-page.canvas-layout-left-rail .node-config-panel,\n.workflow-canvas-page.canvas-layout-left-rail .test-run-panel,\n.workflow-canvas-page.canvas-layout-left-rail .ops-panel',
    )

    expect(stageAndRailPanelBlock).toContain('position: fixed;')
    expect(stageAndRailPanelBlock).toContain('top: calc(4.625rem + var(--debug-dock-gap));')
    expect(stageAndRailPanelBlock).toContain('right: calc(-1 * (var(--workflow-side-panel-width) - var(--workflow-panel-peek-width)))')
  })

  it('keeps the debug dock anchored as an overlay with non-zero minimum width and height', () => {
    const content = readWorkflowCreateSource()
    const dockBlock = extractSelectorBlock(content, '.workflow-debug-dock')

    expect(dockBlock).toMatch(/position:\s*fixed;/)
    expect(dockBlock).toContain('min-width: var(--debug-dock-min-width);')
    expect(dockBlock).toContain('min-height: var(--debug-dock-min-height);')
  })
})
