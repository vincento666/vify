// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readdirSync, readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, extname, join, relative, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const sourceRoot = resolve(projectRoot, 'src')

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry: any) => {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) return sourceFiles(path)
    if (!['.vue', '.css'].includes(extname(entry.name))) return []
    return [path]
  })
}

function styleBlocks(content: string, file: string) {
  if (file.endsWith('.css')) return [content]
  return Array.from(content.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g), (match) => match[1])
}

function collectMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern), (match) => match[0])
}

function isAllowedCssPx(match: string) {
  if (/^@media/.test(match)) return true
  if (/^border(?:-[a-z]+)?:\s*1px\b/.test(match)) return true
  if (/^outline:\s*1px\b/.test(match)) return true
  if (/^box-shadow:/.test(match)) return true
  return false
}

describe('frontend rem scale closure', () => {
  it('keeps all Vue/CSS visual sizing rem-based or explicitly allowlisted', () => {
    const visualCssPxPattern = /(?<![-\w])(?:@media[^{]+|box-shadow|font-size|line-height|padding(?:-[a-z]+)?|margin(?:-[a-z]+)?|gap|grid-template-columns|background-size|min-width|max-width|min-height|max-height|width|height|border(?:-[a-z]+)?|border-radius|outline|top|right|bottom|left)\s*:\s*(?!1px\b)[^;\n{]*px\b/g
    const templateVisualSizePattern = /(?<![-:])(?:width|min-width|max-width|label-width|image-size|size)="[0-9.]+px"|:(?:width|min-width|max-width|image-size|size)="[0-9.]+"|style="[^"]*[0-9.]+px/g

    const matches = sourceFiles(sourceRoot).flatMap((absoluteFile) => {
      const file = relative(projectRoot, absoluteFile)
      const content = readFileSync(absoluteFile, 'utf8')
      return [
        ...styleBlocks(content, file).flatMap((block) => collectMatches(block, visualCssPxPattern)),
        ...collectMatches(content, templateVisualSizePattern),
      ]
        .filter((match) => !isAllowedCssPx(match))
        .map((match) => `${file}: ${match}`)
    })

    expect(matches).toEqual([])
  })
})
