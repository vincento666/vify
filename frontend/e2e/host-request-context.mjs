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

async function createWorkflow(page, stamp) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `023.2 Host Workflow ${stamp}`,
      description: 'host request context e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['userMessage'], ui: { position: { x: 140, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.userMessage}}', ui: { position: { x: 700, y: 180 } } } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create workflow')
}

function findAudit(audit, action, resourceType, resourceId) {
  return audit.find(record => (
    record.action === action
    && record.resourceType === resourceType
    && String(record.resourceId) === String(resourceId)
  ))
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()
  const workflow = await createWorkflow(page, stamp)
  await page.addInitScript(() => {
    globalThis.__HIFY_HOST__ = {
      actorId: 'e2e-host-user',
      actorName: 'E2E Host User',
      tenantId: 'e2e-tenant',
      orgId: 'e2e-org',
      roles: ['builder'],
      permissions: ['workflow:run', 'workflow:publish'],
      source: 'e2e-host-shell',
      requestId: 'e2e-0232',
    }
  })

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.canvas-actions').getByRole('button', { name: '试运行', exact: true }).click()
  const testPanel = page.getByTestId('test-run-panel')
  await testPanel.waitFor({ state: 'visible', timeout: 5000 })
  await testPanel.getByPlaceholder('输入 userMessage').fill('host context')
  await testPanel.getByRole('button', { name: '运行', exact: true }).click()
  await testPanel.getByTestId('workflow-run-output').waitFor({ state: 'visible', timeout: 10000 })

  await page.getByRole('button', { name: '发布', exact: true }).click()
  const publishDialog = page.getByTestId('workflow-publish-dialog')
  await publishDialog.waitFor({ state: 'visible', timeout: 5000 })
  await publishDialog.getByRole('button', { name: '确认发布' }).click()
  await publishDialog.getByText('PUBLISHED').waitFor({ state: 'visible', timeout: 10000 })

  const audit = await unwrap(
    await page.request.get(`${baseUrl}/api/v1/audit-records`, { params: { pageSize: 200 } }),
    'audit records',
  )
  const run = audit.list.find(record => (
    record.action === 'WORKFLOW_RUN'
    && record.resourceType === 'WORKFLOW_RUN'
    && record.metadata?.workflowId === workflow.id
  ))
  const published = findAudit(audit.list, 'WORKFLOW_PUBLISH', 'WORKFLOW', workflow.id)
  assert(run, 'Expected WORKFLOW_RUN audit row')
  assert(published, 'Expected WORKFLOW_PUBLISH audit row')
  assert(run.actor === 'e2e-host-user', `Expected host actor on run, got ${run.actor}`)
  assert(run.metadata?.requestContext?.tenantId === 'e2e-tenant', 'Expected host tenant in run audit metadata')
  assert(published.actor === 'e2e-host-user', `Expected host actor, got ${published.actor}`)
  assert(published.metadata?.requestContext?.tenantId === 'e2e-tenant', 'Expected host tenant in audit metadata')
  assert(published.metadata?.requestContext?.source === 'e2e-host-shell', 'Expected host source in audit metadata')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS host request context e2e workflow=${workflow.id}`)
} finally {
  await browser.close()
}
