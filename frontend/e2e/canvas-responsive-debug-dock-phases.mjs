import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { chromium } from 'playwright'
import { resolveFrontendServer } from './support/dev-server.mjs'

const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''
const measurementsPath = process.env.HIFY_E2E_MEASUREMENTS || ''

const routes = [
  { path: '/workflows/create', label: 'workflow' },
  { path: '/chatflows/create', label: 'chatflow' },
]

const phases = [
  { width: 1536, expected: 'wide', rightPanel: 'full' },
  { width: 896, expected: 'right-anchored', rightPanel: 'full' },
  { width: 840, expected: 'right-shelved', rightPanel: 'peek' },
  { width: 740, expected: 'stage-shelved', rightPanel: 'peek' },
  { width: 620, expected: 'left-rail', rightPanel: 'peek' },
]

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function visibleWidth(rect, viewportWidth) {
  if (!rect) return 0
  return Math.max(0, Math.min(rect.right, viewportWidth) - Math.max(rect.left, 0))
}

async function openCanvasSurfaces(page, path) {
  await page.setViewportSize({ width: 1536, height: 900 })
  await page.goto(`${server.baseUrl}${path}`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="end"]').click()
  await page.getByTestId('node-config-panel').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.canvas-actions').getByRole('button', { name: '调试详情', exact: true }).click()
  await page.getByTestId('workflow-debug-dock').waitFor({ state: 'visible', timeout: 10000 })
}

async function measure(page) {
  return page.evaluate(() => {
    const rect = (selector) => {
      const element = document.querySelector(selector)
      if (!element) return null
      const box = element.getBoundingClientRect()
      return {
        left: box.left,
        right: box.right,
        top: box.top,
        bottom: box.bottom,
        width: box.width,
        height: box.height,
      }
    }
    const rootStyle = getComputedStyle(document.documentElement)
    return {
      phase: document.querySelector('.workflow-canvas-page')?.getAttribute('data-layout-phase'),
      rootFont: Number.parseFloat(rootStyle.fontSize),
      viewportWidth: window.innerWidth,
      documentOverflowX: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
      workbench: rect('[data-testid="workflow-canvas"]'),
      resourcePanel: rect('[data-testid="canvas-resource-panel"]'),
      stage: rect('.canvas-stage-shell'),
      nodeConfig: rect('[data-testid="node-config-panel"]'),
      debugDock: rect('[data-testid="workflow-debug-dock"]'),
    }
  })
}

const server = await resolveFrontendServer()
const browser = await chromium.launch()
const allMeasurements = []

try {
  for (const route of routes) {
    const page = await browser.newPage({ viewport: { width: 1536, height: 900 }, deviceScaleFactor: 1 })
    try {
      await openCanvasSurfaces(page, route.path)
      for (const phase of phases) {
        await page.setViewportSize({ width: phase.width, height: 900 })
        await page.waitForTimeout(120)
        const snapshot = await measure(page)
        const rightVisible = visibleWidth(snapshot.nodeConfig, phase.width)
        const debugVisible = visibleWidth(snapshot.debugDock, phase.width)
        const resourceVisible = visibleWidth(snapshot.resourcePanel, phase.width)
        const record = { route: route.label, ...phase, rightVisible, debugVisible, resourceVisible, snapshot }
        allMeasurements.push(record)

        assert(snapshot.phase === phase.expected, `${route.label} ${phase.width}: expected ${phase.expected}, got ${snapshot.phase}`)
        assert(snapshot.documentOverflowX === 0, `${route.label} ${phase.width}: document should not horizontally overflow`)
        assert(snapshot.nodeConfig, `${route.label} ${phase.width}: expected node config panel`)
        assert(snapshot.debugDock, `${route.label} ${phase.width}: expected debug dock`)
        assert(snapshot.resourcePanel, `${route.label} ${phase.width}: expected left resource panel`)

        if (phase.rightPanel === 'full') {
          assert(
            rightVisible >= snapshot.nodeConfig.width - 2,
            `${route.label} ${phase.width}: right panel should be fully visible, got ${rightVisible}/${snapshot.nodeConfig.width}`,
          )
          assert(
            snapshot.nodeConfig.right <= phase.width + 1,
            `${route.label} ${phase.width}: right panel should anchor inside viewport, got right=${snapshot.nodeConfig.right}`,
          )
        } else {
          assert(
            rightVisible >= 28 && rightVisible <= 48,
            `${route.label} ${phase.width}: shelved right panel should leave only a peek, got ${rightVisible}`,
          )
        }

        if (phase.expected === 'stage-shelved' || phase.expected === 'left-rail') {
          assert(snapshot.stage.width >= 616, `${route.label} ${phase.width}: stage should keep a usable clipped width`)
          assert(snapshot.debugDock.width >= 588, `${route.label} ${phase.width}: debug dock should keep min width`)
          assert(snapshot.debugDock.height >= 252, `${route.label} ${phase.width}: debug dock should keep min height`)
        }
        if (phase.expected === 'left-rail') {
          assert(resourceVisible >= 238, `${route.label} ${phase.width}: left rail should remain usable, got ${resourceVisible}`)
          assert(snapshot.resourcePanel.left >= -1, `${route.label} ${phase.width}: left rail should stay anchored`)
        }

        if (screenshotDir) {
          mkdirSync(screenshotDir, { recursive: true })
          await page.screenshot({ path: `${screenshotDir}/${route.label}-${phase.expected}-${phase.width}.png`, fullPage: true })
        }
      }
    } finally {
      await page.close()
    }
  }
} finally {
  await browser.close()
  await server.close()
}

if (measurementsPath) {
  mkdirSync(dirname(measurementsPath), { recursive: true })
  writeFileSync(measurementsPath, `${JSON.stringify(allMeasurements, null, 2)}\n`)
}

console.log(JSON.stringify({ baseUrl: server.baseUrl, measurements: allMeasurements }, null, 2))
console.log('PASS canvas responsive debug dock phases e2e')
