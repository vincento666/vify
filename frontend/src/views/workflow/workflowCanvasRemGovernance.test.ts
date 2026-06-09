// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')

const governedFiles = [
  'src/views/workflow/WorkflowModuleTabs.vue',
  'src/views/workflow/ChatflowCreate.vue',
  'src/views/workflow/WorkflowCreate.vue',
]

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

function styleBlocks(content: string) {
  return Array.from(content.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g), (match) => match[1])
}

function collectMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern), (match) => match[0])
}

function isAllowedCanvasCssPx(match: string) {
  return /:\s*1px$/.test(match) || /^max-width:\s*\d+px$/.test(match)
}

describe('workflow canvas rem governance', () => {
  it('keeps workflow and chatflow canvas chrome on rem visual sizing', () => {
    const visualCssPxPattern = /(?<![-\w])(?:font-size|line-height|padding(?:-[a-z]+)?|margin(?:-[a-z]+)?|gap|grid-template-columns|background-size|min-width|max-width|min-height|max-height|width|height|border-radius|top|right|bottom|left)\s*:\s*(?!1px\b)[^;\n]*px\b/g
    const templateVisualSizePattern = /(?<![-:])(?:width|min-width|max-width|label-width|size)="[0-9.]+(?:px)?"|:(?:width|min-width|max-width|size)="[0-9.]+"|style="[^"]*[0-9.]+px/g

    const matches = governedFiles.flatMap((file) => {
      const content = readProjectFile(file)
      return [
        ...styleBlocks(content).flatMap((block) => collectMatches(block, visualCssPxPattern)),
        ...collectMatches(content, templateVisualSizePattern),
      ]
        .filter((match) => !isAllowedCanvasCssPx(match))
        .map((match) => `${file}: ${match}`)
    })

    expect(matches).toEqual([])
  })

  it('keeps graph geometry as explicit numeric coordinates', () => {
    const content = readProjectFile('src/views/workflow/WorkflowCreate.vue')

    expect(content).toContain(':default-viewport="{ x: 0, y: 0, zoom: 1 }"')
    expect(content).toContain('const offset = graph.value.nodes.length * 32')
    expect(content).toContain('addWorkflowNode(graph.value, type, { x: 360 + offset, y: 260 + offset })')
    expect(content).toContain('event.node.position')
  })

  it('anchors endpoint affordances from the original dot size instead of compounding hover scale', () => {
    const content = readProjectFile('src/views/workflow/WorkflowCreate.vue')

    expect(content).toContain('--node-port-dot-size: 1rem;')
    expect(content).toContain('--node-port-hit-size: 3rem;')
    expect(content).toContain('--node-port-scale: 1;')
    expect(content).toContain('--node-port-scale: 1.2;')
    expect(content).toContain('width: var(--node-port-dot-size);')
    expect(content).toContain('height: var(--node-port-dot-size);')
    expect(content).toContain('width: var(--node-port-hit-size);')
    expect(content).toContain('height: var(--node-port-hit-size);')
    expect(content).toContain('right: calc(var(--node-port-dot-size) / -2);')
    expect(content).toContain('left: calc(var(--node-port-dot-size) / -2);')
  })
})
