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

async function createWorkflow(page) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `Node Test Run Panel Parity ${Date.now()}`,
        description: 'node test run panel parity e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 80, y: 160 } } } },
          {
            nodeKey: 'selector',
            type: 'CONDITION',
            name: '选择器',
            config: {
              conditionBranches: [{ key: 'vip', label: '会员', conditions: [{ left: '{{start.USER_INPUT}}', operator: 'equals', right: 'vip' }] }],
              defaultBranch: 'default',
              ui: { position: { x: 360, y: 120 } },
            },
          },
          {
            nodeKey: 'aggregation',
            type: 'VARIABLE_AGGREGATION',
            name: '变量聚合',
            config: {
              strategy: 'first_non_empty',
              groups: [{ name: 'selected', type: 'string', variables: [{ value: '{{start.USER_INPUT}}' }] }],
              ui: { position: { x: 680, y: 120 } },
            },
          },
          {
            nodeKey: 'llm',
            type: 'LLM',
            name: '大模型',
            config: {
              model: 'gpt-4.1-mini',
              prompt: 'echo {{start.USER_INPUT}}',
              outputVariable: 'answer',
              ui: { position: { x: 1000, y: 120 } },
            },
          },
          {
            nodeKey: 'code',
            type: 'CODE',
            name: '代码',
            config: {
              language: 'python',
              inputParameters: [{ name: 'input', type: 'string', valueMode: 'reference', value: '{{start.USER_INPUT}}' }],
              code: "result = {'output': 'TEXT ' + str(inputs.get('input', ''))}",
              outputParameters: [{ name: 'output', type: 'string' }],
              ui: { position: { x: 1000, y: 360 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { output: '{{code.output}}', outputVariable: 'final', ui: { position: { x: 1300, y: 160 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'selector', condition: null },
          { sourceNodeKey: 'selector', targetNodeKey: 'aggregation', condition: 'vip' },
          { sourceNodeKey: 'aggregation', targetNodeKey: 'llm', condition: null },
          { sourceNodeKey: 'llm', targetNodeKey: 'code', condition: null },
          { sourceNodeKey: 'code', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create workflow',
  )
}

async function openConfig(page, selector) {
  const configClose = page.getByRole('button', { name: '关闭配置', exact: true })
  if (await configClose.isVisible()) await configClose.click()
  await page.locator(selector).click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  return panel
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const workflow = await createWorkflow(page)
  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })

  let panel = await openConfig(page, '.vue-flow__node[data-id="selector"]')
  assert(await panel.getByRole('button', { name: '试运行当前节点', exact: true }).count() === 0, 'Selector must not expose selected-node run')

  panel = await openConfig(page, '.vue-flow__node[data-id="aggregation"]')
  assert(await panel.getByRole('button', { name: '试运行当前节点', exact: true }).count() === 0, 'Variable aggregation must not expose selected-node run')

  panel = await openConfig(page, '.vue-flow__node[data-id="llm"]')
  assert(await panel.getByRole('button', { name: '试运行当前节点', exact: true }).count() === 1, 'LLM should expose selected-node run')
  panel = await openConfig(page, '.vue-flow__node[data-id="code"]')
  assert(await panel.getByRole('button', { name: '试运行当前节点', exact: true }).count() === 1, 'Code should expose selected-node run')
  await panel.getByRole('button', { name: '试运行当前节点', exact: true }).click()
  const drawer = page.getByTestId('node-test-drawer')
  await drawer.waitFor({ state: 'visible', timeout: 5000 })
  const drawerText = await drawer.innerText()
  for (const label of ['试运行', '查看日志', '试运行输入']) {
    assert(drawerText.includes(label), `Node test drawer should include ${label}, got: ${drawerText}`)
  }
  for (const label of ['JSON模式', 'AI 补全']) {
    assert(!drawerText.includes(label), `Node test drawer should not include ${label}, got: ${drawerText}`)
  }
  assert(await drawer.locator('.node-test-input-actions').count() === 0, 'Node test drawer should not expose JSON/AI input toolbar')
  await drawer.locator('.node-test-input-row', { hasText: 'input' }).locator('input').fill('123')
  await drawer.getByRole('button', { name: '运行', exact: true }).click()
  await drawer.locator('.node-test-status.success').waitFor({ state: 'visible', timeout: 60000 })
  const readableBlocks = await drawer.locator('.node-test-readable-block').evaluateAll((blocks) =>
    blocks.map((block) => ({
      title: block.querySelector('strong')?.textContent?.trim(),
      text: block.textContent?.trim(),
    })),
  )
  for (const title of ['输入', '推理内容', '技能调用', '输出']) {
    assert(readableBlocks.some((block) => block.title === title), `Expected readable result block ${title}, got ${JSON.stringify(readableBlocks)}`)
  }
  assert(
    await drawer.locator('.node-test-result-block dl').count() === 0,
    'Node test result should not use a raw definition-list JSON view',
  )

  await drawer.getByRole('button', { name: '关闭节点试运行', exact: true }).click()
  await page.getByTestId('canvas-bottom-toolbar').getByRole('button', { name: '试运行', exact: true }).click()
  const runPanel = page.getByTestId('test-run-panel')
  await runPanel.waitFor({ state: 'visible', timeout: 5000 })
  const runText = await runPanel.innerText()
  for (const label of ['试运行', '查看日志', '试运行输入']) {
    assert(runText.includes(label), `Workflow run panel should include ${label}, got: ${runText}`)
  }
  for (const label of ['JSON模式', 'AI 补全']) {
    assert(!runText.includes(label), `Workflow run panel should not include ${label}, got: ${runText}`)
  }
  assert(await runPanel.locator('.node-test-input-actions').count() === 0, 'Workflow run panel should not expose JSON/AI input toolbar')
  const runPanelGeometry = await runPanel.evaluate((panel) => {
    const style = getComputedStyle(panel)
    const probe = document.createElement('div')
    probe.style.position = 'absolute'
    probe.style.width = 'var(--workflow-panel-gap)'
    panel.appendChild(probe)
    const gap = getComputedStyle(probe).width
    probe.remove()
    return {
      right: style.right,
      top: style.top,
      bottom: style.bottom,
      gap,
    }
  })
  const panelGap = Number.parseFloat(runPanelGeometry.gap)
  const panelOffsets = [runPanelGeometry.right, runPanelGeometry.top, runPanelGeometry.bottom].map((value) => Number.parseFloat(value))
  assert(
    panelOffsets.every((value) => Math.abs(value - panelGap) < 0.01),
    `Expected run panel offsets to use unified panel gap, got ${JSON.stringify(runPanelGeometry)}`,
  )

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })
  console.log('PASS workflow node-test run-panel parity e2e')
} finally {
  await browser.close()
}
