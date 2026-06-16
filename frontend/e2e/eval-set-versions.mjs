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
  await page.getByTestId('eval-set-version-tag').waitFor({ state: 'visible', timeout: 10000 })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const setName = `020.1 Eval Set ${stamp}`
  const evalSet = await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets`, {
    data: { name: setName, description: 'version e2e' },
  }), 'create eval set')
  const evalCase = await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/cases`, {
    data: { input: 'hello', expectedOutput: 'world', tags: ['v1'], metadata: {} },
  }), 'create eval case')

  await openEvalSet(page, setName)
  const tag = page.getByTestId('eval-set-version-tag')
  const submit = page.getByTestId('submit-eval-set-version')
  await tag.getByText('草稿', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  assert(await submit.isEnabled(), 'Expected submit version button enabled for draft')
  await submit.click()
  await tag.getByText('v0.0.1', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  assert(!(await submit.isEnabled()), 'Expected submit version button disabled after clean submit')

  const records = page.getByTestId('eval-set-version-records')
  await records.getByText('v0.0.1', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  await unwrap(await page.request.put(`${baseUrl}/api/v1/eval-cases/${evalCase.id}`, {
    data: { input: 'hello edited', expectedOutput: 'world edited', tags: ['v2'], metadata: {} },
  }), 'edit eval case')
  await openEvalSet(page, setName)
  await tag.getByText('v0.0.1 后有草稿变更', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  assert(await submit.isEnabled(), 'Expected submit enabled after draft change')
  await submit.click()
  await tag.getByText('v0.0.2', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await records.getByText('v0.0.2', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await records.getByText('v0.0.1', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  const versions = await unwrap(await page.request.get(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/versions`), 'list versions')
  assert(versions.total === 2, `Expected two versions, got ${versions.total}`)
  assert(versions.list[1].caseSnapshot[0].input === 'hello', 'Expected v0.0.1 snapshot immutable')
  assert(versions.list[0].caseSnapshot[0].input === 'hello edited', 'Expected v0.0.2 snapshot updated')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS eval set versions e2e evalSet=${evalSet.id}`)
} finally {
  await browser.close()
}
