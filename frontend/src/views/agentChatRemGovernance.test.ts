// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')

const governedFiles = [
  'src/views/agent/AgentWorkbench.vue',
  'src/views/chat/ChatView.vue',
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

function isAllowedCssPx(match: string) {
  return /:\s*1px$/.test(match) || /^max-width:\s*\d+px$/.test(match)
}

describe('agent workbench and chat rem governance', () => {
  it('keeps workbench and chat visual sizing on rem units', () => {
    const visualCssPxPattern = /(?<![-\w])(?:font-size|line-height|padding(?:-[a-z]+)?|margin(?:-[a-z]+)?|gap|grid-template-columns|background-size|min-width|max-width|min-height|max-height|width|height|border-radius|top|right|bottom|left)\s*:\s*(?!1px\b)[^;\n]*px\b/g
    const templateVisualSizePattern = /(?<![-:])(?:width|min-width|max-width|label-width|size)="[0-9.]+(?:px)?"|:(?:width|min-width|max-width|size)="[0-9.]+"|style="[^"]*[0-9.]+px/g

    const matches = governedFiles.flatMap((file) => {
      const content = readProjectFile(file)
      return [
        ...styleBlocks(content).flatMap((block) => collectMatches(block, visualCssPxPattern)),
        ...collectMatches(content, templateVisualSizePattern),
      ]
        .filter((match) => !isAllowedCssPx(match))
        .map((match) => `${file}: ${match}`)
    })

    expect(matches).toEqual([])
  })
})
