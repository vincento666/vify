// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import { resolveCanvasResponsiveLayout } from './canvasResponsiveLayout'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

function workflowCreateSource() {
  return readFileSync(resolve(projectRoot, 'src/views/workflow/WorkflowCreate.vue'), 'utf8')
}

describe('workflow canvas responsive layout policy', () => {
  it('keeps right panels edge-anchored before shelving them, then clips the stage, then leaves the left rail primary', () => {
    expect(resolveCanvasResponsiveLayout({ viewportWidth: 96, rem: 1 })).toMatchObject({
      phase: 'wide',
      className: 'canvas-layout-wide',
      rightPanelMode: 'full',
      stageMode: 'fit',
      debugDockMode: 'fluid',
    })

    expect(resolveCanvasResponsiveLayout({ viewportWidth: 84, rem: 1 })).toMatchObject({
      phase: 'right-anchored',
      className: 'canvas-layout-right-anchored',
      rightPanelMode: 'full',
      stageMode: 'fit',
      debugDockMode: 'locked',
    })

    expect(resolveCanvasResponsiveLayout({ viewportWidth: 58, rem: 1 })).toMatchObject({
      phase: 'right-shelved',
      className: 'canvas-layout-right-shelved',
      rightPanelMode: 'peek',
      stageMode: 'fit',
      debugDockMode: 'locked',
    })

    expect(resolveCanvasResponsiveLayout({ viewportWidth: 50, rem: 1 })).toMatchObject({
      phase: 'stage-shelved',
      className: 'canvas-layout-stage-shelved',
      rightPanelMode: 'peek',
      stageMode: 'clipped',
      debugDockMode: 'locked',
    })

    expect(resolveCanvasResponsiveLayout({ viewportWidth: 44, rem: 1 })).toMatchObject({
      phase: 'left-rail',
      className: 'canvas-layout-left-rail',
      rightPanelMode: 'peek',
      stageMode: 'mostly-hidden',
      debugDockMode: 'locked',
    })
  })

  it('wires the policy into workflow/chatflow canvas chrome and debug dock CSS', () => {
    const content = workflowCreateSource()

    expect(content).toContain('responsiveCanvasLayout.className')
    expect(content).toContain('--workflow-panel-peek-width:')
    expect(content).toContain('--debug-dock-min-width:')
    expect(content).toContain('min-width: var(--debug-dock-min-width);')
    expect(content).toContain('.workflow-canvas-page.canvas-layout-right-anchored .node-config-panel')
    expect(content).toContain('.workflow-canvas-page.canvas-layout-right-shelved .node-config-panel')
    expect(content).toContain('.workflow-canvas-page.canvas-layout-stage-shelved .canvas-workbench')
    expect(content).toContain('.workflow-canvas-page.canvas-layout-left-rail .canvas-stage-shell')
    expect(content).toContain('right: calc(-1 * (var(--workflow-side-panel-width) - var(--workflow-panel-peek-width)))')
  })
})
