import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const timestamp = Date.now()
const evalSetName = `E2E Eval Set ${timestamp}`
const updatedDescription = `E2E updated regression set ${timestamp}`

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: 'Eval Sets' }).click()
  await assertBodyIncludes(page, '创建评测集')

  await page.getByTestId('create-eval-set').click()
  await page.getByPlaceholder('请输入评测集名称').fill(evalSetName)
  await page.getByPlaceholder('描述适用场景').fill('E2E manual regression set')
  await page.getByTestId('save-eval-set').click()
  await page.locator('h4', { hasText: evalSetName }).waitFor({ state: 'visible', timeout: 5000 })
  await assertBodyIncludes(page, '0 cases')

  await page.getByRole('button', { name: '添加用例' }).first().click()
  await page.getByPlaceholder('用户输入或测试问题').fill('用户问：7 天内可以退款吗？')
  await page.getByPlaceholder('期望回答包含的标准答案').fill('7 天内可以申请退款')
  await page.getByPlaceholder('用英文逗号分隔，如 refund,policy').fill('refund, policy, refund')
  await page.getByTestId('save-eval-case').click()
  await page.getByText('7 天内可以申请退款').waitFor({ state: 'visible', timeout: 5000 })
  await assertBodyIncludes(page, '1 cases')
  await assertBodyIncludes(page, 'refund')
  await assertBodyIncludes(page, 'policy')

  await page.getByRole('button', { name: '编辑用例' }).click()
  await page.getByPlaceholder('期望回答包含的标准答案').fill('7 天内可以在线申请退款')
  await page.getByTestId('save-eval-case').click()
  await page.getByText('7 天内可以在线申请退款').waitFor({ state: 'visible', timeout: 5000 })

  await page.getByRole('button', { name: '编辑' }).first().click()
  await page.getByPlaceholder('描述适用场景').fill(updatedDescription)
  await page.getByTestId('save-eval-set').click()
  await page.locator('.el-dialog', { hasText: '编辑评测集' }).waitFor({ state: 'hidden', timeout: 5000 })
  await page.getByText(updatedDescription).waitFor({ state: 'visible', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS evaluation eval sets CRUD e2e ${evalSetName}`)
} finally {
  await browser.close()
}
