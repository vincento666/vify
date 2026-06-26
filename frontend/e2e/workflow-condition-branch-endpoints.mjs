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

async function conditionPortLabels(page) {
  return page.locator('.vue-flow__node[data-id="router"] [data-testid="condition-source-port"]').evaluateAll((nodes) =>
    nodes.map((node) => node.getAttribute('data-branch-label') || ''),
  )
}

async function conditionBranchBlocks(page) {
  return page.locator('.vue-flow__node[data-id="router"] [data-testid="condition-branch-block"]').evaluateAll((nodes) =>
    nodes.map((node) => node.textContent?.replace(/\s+/g, ' ').trim() || ''),
  )
}

async function conditionPortAlignment(page) {
  return page.locator('.vue-flow__node[data-id="router"]').evaluate((node) => {
    const blocks = Array.from(node.querySelectorAll('[data-testid="condition-branch-block"]'))
    const ports = Array.from(node.querySelectorAll('[data-testid="condition-source-port"]'))
    return blocks.map((block, index) => {
      const blockRect = block.getBoundingClientRect()
      const portRect = ports[index]?.getBoundingClientRect()
      return {
        blockCenterY: blockRect.top + blockRect.height / 2,
        portCenterY: portRect ? portRect.top + portRect.height / 2 : null,
      }
    })
  })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `Condition Branch Endpoints ${Date.now()}`,
      description: 'condition branch endpoint e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 260 } } } },
        {
          nodeKey: 'router',
          type: 'CONDITION',
          name: '选择器_1',
          config: {
            conditionBranches: [{
              key: 'vip',
              name: 'VIP 客户',
              logic: 'AND',
              conditions: [{ left: '{{start.USER_INPUT}}', operator: 'equals', right: 'vip' }],
            }],
            defaultBranch: 'default',
            defaultBranchName: '普通客户',
            ui: { position: { x: 540, y: 220 } },
          },
        },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{router.route}}', ui: { position: { x: 980, y: 260 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'router', condition: null },
        { sourceNodeKey: 'router', targetNodeKey: 'end', condition: 'vip' },
      ],
    },
  }), 'create condition endpoint workflow')

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  const routerNode = page.locator('.vue-flow__node[data-id="router"]')
  await routerNode.waitFor({ state: 'visible', timeout: 5000 })

  let labels = await conditionPortLabels(page)
  assert(
    labels.length === 2 && labels.includes('VIP 客户') && labels.includes('普通客户'),
    `Condition node must render semantic branch names on source endpoints, got ${JSON.stringify(labels)}`,
  )

  let branchBlocks = await conditionBranchBlocks(page)
  assert(
    branchBlocks.length === 2 && branchBlocks.some((text) => text.includes('如果') && text.includes('VIP 客户')) && branchBlocks.some((text) => text.includes('否则') && text.includes('普通客户')),
    `Condition card must render branch name blocks, got ${JSON.stringify(branchBlocks)}`,
  )
  const routerText = await routerNode.textContent()
  assert(!routerText.includes('输入') && !routerText.includes('输出'), `Condition card must not render generic input/output rows, got ${routerText}`)
  assert(
    (routerText.match(/VIP 客户/g) || []).length === 1 && (routerText.match(/普通客户/g) || []).length === 1,
    `Condition card must not render duplicate visible endpoint labels, got ${routerText}`,
  )
  for (const row of await conditionPortAlignment(page)) {
    assert(row.portCenterY !== null, `Condition branch must have a matching source endpoint, got ${JSON.stringify(row)}`)
    assert(Math.abs(row.blockCenterY - row.portCenterY) <= 4, `Condition source endpoint must align with branch block center, got ${JSON.stringify(row)}`)
  }

  await routerNode.click()
  await page.getByTestId('node-config-panel').waitFor({ state: 'visible', timeout: 5000 })
  const panelText = await page.getByTestId('node-config-panel').textContent()
  assert(panelText.includes('优先级 1'), `Condition panel must expose selector branch priority, got ${panelText}`)
  assert(panelText.includes('VIP 客户') && panelText.includes('普通客户'), `Condition panel must visibly render semantic branch names, got ${panelText}`)
  assert(!panelText.includes('点击编辑'), `Condition branch headers must be directly editable without visible helper copy, got ${panelText}`)
  assert(!panelText.includes('全部满足') && !panelText.includes('任一满足'), `Condition panel must not expose generic all/any logic selectors, got ${panelText}`)
  assert(!panelText.includes('输入参数') && !panelText.includes('输出参数'), `Condition panel must not expose generic parameter sections, got ${panelText}`)
  const conditionSection = page.getByTestId('config-section-条件分支')
  const conditionSectionText = await conditionSection.textContent()
  assert(
    (conditionSectionText.match(/条件分支/g) || []).length === 1,
    `Condition branch section must not repeat its title as a field label or text button, got ${conditionSectionText}`,
  )
  const conditionSectionHeader = conditionSection.locator('.section-title')
  assert(
    await conditionSectionHeader.getByRole('button', { name: '添加条件分支', exact: true }).count() === 1,
    'Condition branch add action must be in the section header',
  )
  assert(
    await conditionSection.getByTestId('condition-branch-editor').getByRole('button', { name: '添加条件分支', exact: true }).count() === 0,
    'Condition branch editor must not render a duplicate bottom add-branch button',
  )

  await conditionSectionHeader.getByRole('button', { name: '添加条件分支', exact: true }).click()
  await page.waitForTimeout(200)
  await page.getByTestId('condition-branch-title').last().click()
  const branchNameInput = page.getByLabel('分支名称', { exact: true }).last()
  await branchNameInput.fill('高价值订单')
  await branchNameInput.press('Enter')
  await page.waitForTimeout(200)

  labels = await conditionPortLabels(page)
  assert(
    labels.length === 3 && labels.includes('高价值订单'),
    `Renaming a branch header must update the matching source endpoint label, got ${JSON.stringify(labels)}`,
  )
  branchBlocks = await conditionBranchBlocks(page)
  assert(
    branchBlocks.some((text) => text.includes('否则如果') && text.includes('高价值订单')),
    `Renaming a branch header must update the condition card block, got ${JSON.stringify(branchBlocks)}`,
  )
  const updatedRouterText = await routerNode.textContent()
  assert(
    (updatedRouterText.match(/高价值订单/g) || []).length === 1,
    `Renamed branch must not leave an extra visible endpoint label, got ${updatedRouterText}`,
  )
  const updatedPanelText = await page.getByTestId('node-config-panel').textContent()
  assert(updatedPanelText.includes('高价值订单'), `Renamed branch must remain visible in condition panel header, got ${updatedPanelText}`)
  for (const row of await conditionPortAlignment(page)) {
    assert(row.portCenterY !== null, `Condition branch must have a matching source endpoint after rename, got ${JSON.stringify(row)}`)
    assert(Math.abs(row.blockCenterY - row.portCenterY) <= 4, `Condition source endpoint must stay aligned after rename, got ${JSON.stringify(row)}`)
  }

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS workflow condition branch endpoints e2e workflow=${workflow.id}`)
} finally {
  await browser.close()
}
