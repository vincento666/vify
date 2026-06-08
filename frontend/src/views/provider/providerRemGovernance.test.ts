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

function collectMatches(content: string, pattern: RegExp) {
  return Array.from(content.matchAll(pattern), (match) => match[0])
}

describe('provider page rem governance', () => {
  it('keeps provider management visual sizing on rem tokens', () => {
    const content = readProjectFile('src/views/provider/ProviderList.vue')
    const rawVisualPxPattern = /\b(?:font-size|padding(?:-[a-z]+)?|margin(?:-[a-z]+)?|gap|min-width|max-width|min-height|max-height|width|height|border-radius)\s*:\s*(?!1px\b)[^;\n]*\bpx\b/g
    const templatePxPattern = /(?:width|label-width)="[0-9.]+px"|:width="[0-9.]+\"|style="[^"]*[0-9.]+px|height:\s*'[0-9.]+px'/g

    const matches = [
      ...collectMatches(content, rawVisualPxPattern),
      ...collectMatches(content, templatePxPattern),
    ]

    expect(matches).toEqual([])
  })
})
