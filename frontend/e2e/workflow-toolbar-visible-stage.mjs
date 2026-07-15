import { mkdirSync } from 'node:fs'

import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''

const routes = [
  { label: 'workflow', path: '/workflows/create' },
  { label: 'chatflow', path: '/chatflows/create' },
]
const responsiveCases = [
  { label: 'wide', width: 1536, phase: 'wide' },
  { label: 'right-anchored', width: 1200, phase: 'right-anchored' },
  { label: 'right-shelved-896', width: 896, phase: 'right-shelved' },
  { label: 'right-shelved-840', width: 840, phase: 'right-shelved' },
  { label: 'stage-shelved', width: 740, phase: 'stage-shelved', clipped: true },
  { label: 'left-rail', width: 620, phase: 'left-rail', clipped: true },
]

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function visibleInterval(rect, viewportWidth) {
  if (!rect) return null
  const left = Math.max(0, rect.left)
  const right = Math.min(viewportWidth, rect.right)
  return right > left ? { left, right, width: right - left } : null
}

function availableStageInterval(snapshot) {
  const stage = visibleInterval(snapshot.stage, snapshot.viewport.width)
  if (!stage) return null
  const panel = visibleInterval(snapshot.panel, snapshot.viewport.width)
  if (!panel || panel.left >= stage.right || panel.right <= stage.left) return stage
  const right = Math.min(stage.right, panel.left)
  return right > stage.left ? { left: stage.left, right, width: right - stage.left } : null
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

    return {
      phase: document.querySelector('.workflow-canvas-page')?.getAttribute('data-layout-phase'),
      viewport: { width: window.innerWidth, height: window.innerHeight },
      toolbar: rect('[data-testid="canvas-bottom-toolbar"]'),
      resource: rect('[data-testid="canvas-resource-panel"]'),
      stage: rect('.canvas-stage-shell'),
      panel: rect('[data-testid="node-config-panel"]'),
    }
  })
}

function overlaps(a, b) {
  return Boolean(a && b && a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top)
}

function assertToolbarGeometry(snapshot, label, expectedPhase) {
  const visibleStage = availableStageInterval(snapshot)
  const toolbar = snapshot.toolbar

  assert(snapshot.phase === expectedPhase, `${label}: expected ${expectedPhase} phase, got ${snapshot.phase}`)
  assert(toolbar && visibleStage && snapshot.resource, `${label}: expected toolbar, visible stage, and resource rail, got ${JSON.stringify(snapshot)}`)
  assert(
    toolbar.left >= visibleStage.left - 1 && toolbar.right <= visibleStage.right + 1,
    `${label}: toolbar must remain fully inside visible stage, got ${JSON.stringify({ toolbar, visibleStage, snapshot })}`,
  )
  assert(
    Math.abs(toolbar.left + toolbar.width / 2 - (visibleStage.left + visibleStage.right) / 2) <= 2,
    `${label}: toolbar must center in visible stage, got ${JSON.stringify({ toolbar, visibleStage, snapshot })}`,
  )
  assert(
    !overlaps(toolbar, snapshot.resource),
    `${label}: toolbar must not overlap resource rail, got ${JSON.stringify({ toolbar, resource: snapshot.resource, snapshot })}`,
  )
  assert(
    !overlaps(toolbar, snapshot.panel),
    `${label}: toolbar must not overlap the visible panel edge, got ${JSON.stringify({ toolbar, panel: snapshot.panel, snapshot })}`,
  )
}

async function assertVisibleStageToolbar(page, route) {
  for (const scenario of responsiveCases.filter((item) => item.clipped)) {
    await page.setViewportSize({ width: scenario.width, height: 900 })
    await page.goto(`${baseUrl}${route.path}`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(280)
    assertToolbarGeometry(await measure(page), `${route.label}: ${scenario.label} no side panel`, scenario.phase)
  }

  for (const scenario of responsiveCases) {
    await page.setViewportSize({ width: 1536, height: 900 })
    await page.goto(`${baseUrl}${route.path}`, { waitUntil: 'networkidle' })
    const endNode = page.locator('.vue-flow__node[data-id="end"]')
    await endNode.waitFor({ state: 'visible', timeout: 10000 })
    await endNode.click({ force: true })
    await page.getByTestId('node-config-panel').waitFor({ state: 'visible', timeout: 10000 })

    await page.setViewportSize({ width: scenario.width, height: 900 })
    await page.waitForTimeout(280)
    assertToolbarGeometry(await measure(page), `${route.label}: ${scenario.label}`, scenario.phase)

    if (scenario.clipped) {
      await page.locator('[data-testid="workflow-canvas"]').evaluate((element) => {
        element.scrollLeft = Math.max(1, element.scrollWidth - element.clientWidth - 46)
      })
      await page.waitForTimeout(280)
      assertToolbarGeometry(await measure(page), `${route.label}: ${scenario.label} scrolled clipped stage`, scenario.phase)
    }
  }

  if (screenshotDir) {
    mkdirSync(screenshotDir, { recursive: true })
    await page.screenshot({ path: `${screenshotDir}/${route.label}-620-left-rail.png`, fullPage: true })
  }
}

const browser = await chromium.launch()

try {
  for (const route of routes) {
    const page = await browser.newPage({ viewport: { width: 1536, height: 900 } })
    try {
      await assertVisibleStageToolbar(page, route)
    } finally {
      await page.close()
    }
  }
} finally {
  await browser.close()
}

console.log('PASS workflow/chatflow visible-stage toolbar e2e')
