// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { existsSync, readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')

function readSourceFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

describe('legacy Element Plus isolation', () => {
  it('keeps Element Plus out of frontend startup', () => {
    const main = readSourceFile('src/main.ts')

    expect(main).not.toMatch(/from ['"]element-plus['"]/)
    expect(main).not.toMatch(/@element-plus\/icons-vue/)
    expect(main).not.toContain("element-plus/dist/index.css")
    expect(main).not.toContain("styles/element-override.css")
    expect(main).not.toMatch(/app\.use\(ElementPlus\)/)
  })

  it('removes the legacy Element Plus route loader', () => {
    const legacyPath = 'src/app/legacy-element-plus.ts'

    expect(existsSync(resolve(projectRoot, legacyPath))).toBe(false)
  })

  it('keeps package manifests off Element Plus runtime dependencies', () => {
    const packageJson = readSourceFile('package.json')

    expect(packageJson).not.toContain('element-plus')
    expect(packageJson).not.toContain('@element-plus/icons-vue')
  })
})
