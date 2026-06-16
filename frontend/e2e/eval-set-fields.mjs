import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function openEvalSet(page, name) {
  await page.goto(`${baseUrl}/evaluation?tab=eval-sets`, { waitUntil: 'networkidle' })
  await page.getByText(name, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  const card = page.locator('.eval-set-card').filter({ hasText: name })
  await card.getByTestId('view-eval-set-detail').click()
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const setName = `020.2 Field Set ${stamp}`
  const evalSet = await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets`, {
    data: { name: setName, description: 'field e2e' },
  }), 'create eval set')

  await openEvalSet(page, setName)
  await page.getByTestId('edit-eval-set-columns').click()
  const editor = page.getByTestId('eval-set-field-editor')
  await editor.getByText('添加列', { exact: true }).click()
  await editor.locator('input[placeholder="字段键"]').last().fill('reference_output')
  await editor.locator('input[placeholder="字段名称"]').last().fill('Reference')
  await editor.locator('input[type="checkbox"]').last().check()
  await page.getByTestId('save-eval-set-fields').click()
  await page.getByText('Reference', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  const requiredFailure = await page.request.post(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/cases`, {
    data: { input: 'missing', expectedOutput: 'field', tags: [], metadata: {} },
  })
  assert(requiredFailure.status() === 400, `Expected required field API failure, got ${requiredFailure.status()}`)

  await page.getByTestId('add-eval-case').click()
  await page.getByPlaceholder('用户输入或测试问题').fill('refund policy')
  await page.getByPlaceholder('期望回答包含的标准答案').fill('refund answer')
  await page.getByTestId('eval-case-field-reference_output').fill('policy paragraph 9')
  await page.getByTestId('save-eval-case').click()
  await page.getByText('policy paragraph 9', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  const fields = await unwrap(await page.request.get(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/fields`), 'list fields')
  assert(fields.total === 3, `Expected three fields, got ${fields.total}`)
  assert(fields.list[2].key === 'reference_output', 'Expected reference_output field')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS eval set fields e2e evalSet=${evalSet.id}`)
} finally {
  await browser.close()
}
