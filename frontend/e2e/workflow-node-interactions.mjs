import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function dragNode(page, nodeId, deltaX, deltaY) {
  const node = page.locator(`.vue-flow__node[data-id="${nodeId}"]`)
  await node.waitFor({ state: 'visible', timeout: 5000 })
  const before = await node.boundingBox()
  assert(before, `Expected ${nodeId} node to have a bounding box before drag`)
  await page.mouse.move(before.x + before.width / 2, before.y + before.height / 2)
  await page.mouse.down()
  await page.mouse.move(before.x + before.width / 2 + deltaX, before.y + before.height / 2 + deltaY, { steps: 10 })
  await page.mouse.up()
  const after = await node.boundingBox()
  assert(after, `Expected ${nodeId} node to have a bounding box after drag`)
  return { before, after }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Workflow Interactions ${Date.now()}`

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('工作流名称').fill(name)

  const startDrag = await dragNode(page, 'start', 120, 80)
  assert(
    Math.abs(startDrag.after.x - startDrag.before.x) > 40 || Math.abs(startDrag.after.y - startDrag.before.y) > 40,
    'Expected START node to move by mouse drag',
  )

  await page.locator('.vue-flow__node[data-id="start"]').click()
  await page.keyboard.press('Enter')
  assert(await page.locator('.vue-flow__node[data-id="start"]').count() === 1, 'Expected fixed START node to survive keyboard deletion')

  await page.getByRole('button', { name: '添加节点' }).click()
  await page.locator('.node-palette button', { hasText: '大模型' }).click()
  const llmNode = page.locator('.vue-flow__node[data-id="llm_1"]')
  await llmNode.waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.getByLabel('删除节点').count() === 0, 'Expected node card to omit inline delete button')

  await llmNode.click()
  await page.keyboard.press('Enter')
  await llmNode.waitFor({ state: 'detached', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow node drag and keyboard delete e2e')
} finally {
  await browser.close()
}
