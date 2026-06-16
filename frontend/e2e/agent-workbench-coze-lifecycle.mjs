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

async function findEnabledModel(page) {
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      if (String(provider.baseUrl || '').startsWith('mock://')) continue
      for (const model of provider.models ?? []) {
        if (model.enabled) return model.id
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  throw new Error('No enabled model found for Agent Coze lifecycle e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Coze Layout Agent ${Date.now()}`,
        description: 'coze lifecycle shell',
        systemPrompt: 'You are testing the Coze-aligned three-column shell. If the user asks for COZE_DEBUG_OK, return exactly COZE_DEBUG_OK.',
        openingMessage: '你好，我是测试助手。',
        suggestedQuestions: ['如何开始？'],
        modelConfigId,
        temperature: 0.2,
        maxTokens: 512,
        maxContextTurns: 4,
        toolIds: [],
      },
    }),
    'create agent',
  )

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'load' })
  const shell = page.getByTestId('agent-workbench-shell')
  await shell.waitFor({ state: 'visible', timeout: 5000 })

  const persona = page.getByTestId('agent-persona-column')
  const orchestration = page.getByTestId('agent-orchestration-column')
  const preview = page.getByTestId('agent-preview-debug-column')
  await persona.waitFor({ state: 'visible', timeout: 5000 })
  await orchestration.waitFor({ state: 'visible', timeout: 5000 })
  await preview.waitFor({ state: 'visible', timeout: 5000 })

  await persona.getByText('人设与回复逻辑').waitFor({ state: 'visible', timeout: 5000 })
  await persona.locator('.prompt-editor textarea').waitFor({ state: 'visible', timeout: 5000 })
  assert(await persona.getByText('Agent 名称').count() === 0, 'Persona column should not duplicate Agent name')
  assert(await persona.getByText('通用结构').count() === 0, 'Persona column should not expose template recommendation cards')
  await orchestration.getByText('编排').waitFor({ state: 'visible', timeout: 5000 })
  for (const label of ['模型设置', '技能', '知识', '记忆', '对话体验']) {
    await orchestration.getByText(label, { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  }
  assert(await orchestration.getByText('版本与发布', { exact: true }).count() === 0, 'Version/release must not live inside orchestration')
  assert(await orchestration.getByText('访问与分享', { exact: true }).count() === 0, 'Access/sharing must not live inside orchestration')
  await preview.getByText('预览与调试').waitFor({ state: 'visible', timeout: 5000 })
  await preview.getByText('内容由 AI 生成').waitFor({ state: 'visible', timeout: 5000 })

  assert(await page.getByTestId('agent-workbench-nav').count() === 0, 'Section anchor tabs should be removed above columns')
  assert(await orchestration.locator('.editor-toolbar .status-pill').count() === 0, 'Orchestration header should not show capability/runtime pills')
  assert(await page.getByTestId('agent-runtime-summary').count() === 0, 'Default LLM streaming path should not be announced as a visible mode card')
  assert(await preview.getByTestId('preview-target-select').count() === 0, 'Draft-only preview target selector should be hidden until versions exist')
  const debugButtonBox = await preview.getByRole('button', { name: '打开调试详情' }).boundingBox()
  assert(debugButtonBox && debugButtonBox.width <= 34 && debugButtonBox.height <= 34, `Debug action should use compact canvas-toolbar icon sizing: ${JSON.stringify(debugButtonBox)}`)
  const summaryLayout = await orchestration.evaluate(() => {
    const summary = document.querySelector('.module-summary')
    const title = summary?.querySelector('strong')?.getBoundingClientRect()
    const description = summary?.querySelector('span')?.getBoundingClientRect()
    return {
      titleBottom: Math.round(title?.bottom ?? 0),
      descriptionTop: Math.round(description?.top ?? 0),
    }
  })
  assert(summaryLayout.descriptionTop > summaryLayout.titleBottom, `Module summary description should sit below the title: ${JSON.stringify(summaryLayout)}`)
  assert(await page.getByRole('button', { name: '试运行' }).count() === 0, 'Header must not expose a disabled run button; preview panel is the run surface')
  assert(await preview.getByRole('button', { name: '查看日志' }).count() === 0, 'Preview header should not expose shell log button')
  assert(await preview.getByRole('button', { name: '配置' }).count() === 0, 'Preview header should not expose shell config button')
  assert(await page.getByText('单 Agent', { exact: false }).count() > 0, 'Expected Coze-like single Agent mode label')
  assert(await page.getByRole('button', { name: '发布', exact: true }).count() === 1, 'Expected one primary publish action')

  const grid = await shell.evaluate(() => {
    const personaRect = document.querySelector('[data-testid="agent-persona-column"]')?.getBoundingClientRect()
    const orchestrationRect = document.querySelector('[data-testid="agent-orchestration-column"]')?.getBoundingClientRect()
    const previewRect = document.querySelector('[data-testid="agent-preview-debug-column"]')?.getBoundingClientRect()
    return {
      personaX: Math.round(personaRect?.x ?? 0),
      orchestrationX: Math.round(orchestrationRect?.x ?? 0),
      previewX: Math.round(previewRect?.x ?? 0),
      personaWidth: Math.round(personaRect?.width ?? 0),
      orchestrationWidth: Math.round(orchestrationRect?.width ?? 0),
      previewWidth: Math.round(previewRect?.width ?? 0),
    }
  })
  assert(grid.personaX < grid.orchestrationX && grid.orchestrationX < grid.previewX, `Expected left-middle-right columns: ${JSON.stringify(grid)}`)
  assert(grid.personaWidth >= 320 && grid.orchestrationWidth >= 360 && grid.previewWidth >= 320, `Expected stable three-column widths: ${JSON.stringify(grid)}`)

  await preview.getByPlaceholder('输入预览消息').fill('Return marker COZE_DEBUG_OK')
  await preview.getByRole('button', { name: '发送预览消息', exact: true }).click()
  await preview.getByText('COZE_DEBUG_OK', { exact: true }).waitFor({ state: 'visible', timeout: 60000 })
  await preview.getByRole('button', { name: '打开调试详情' }).click()
  const debugPanel = page.getByTestId('agent-debug-detail-panel')
  await debugPanel.getByText('调试详情').waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('调用树').waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('火焰图').waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('节点详情').waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('RunID：preview-session-', { exact: false }).waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('服务端耗时', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  const focusState = await debugPanel.evaluate((element) => document.activeElement === element)
  assert(focusState, 'Expected debug detail panel to receive focus when opened')
  await debugPanel.getByRole('button', { name: '火焰图' }).click()
  await debugPanel.getByText('用户输入 UserInput').waitFor({ state: 'visible', timeout: 5000 })
  const debugGrid = await shell.evaluate(() => {
    const shellEl = document.querySelector('[data-testid="agent-workbench-shell"]')
    const previewRect = document.querySelector('[data-testid="agent-preview-debug-column"]')?.getBoundingClientRect()
    const personaRect = document.querySelector('[data-testid="agent-persona-column"]')?.getBoundingClientRect()
    const orchestrationRect = document.querySelector('[data-testid="agent-orchestration-column"]')?.getBoundingClientRect()
    const debugRect = document.querySelector('[data-testid="agent-debug-detail-panel"]')?.getBoundingClientRect()
    return {
      shellClientWidth: shellEl?.clientWidth ?? 0,
      shellScrollWidth: shellEl?.scrollWidth ?? 0,
      previewX: Math.round(previewRect?.x ?? 0),
      debugX: Math.round(debugRect?.x ?? 0),
      personaWidth: Math.round(personaRect?.width ?? 0),
      orchestrationWidth: Math.round(orchestrationRect?.width ?? 0),
      previewWidth: Math.round(previewRect?.width ?? 0),
      debugWidth: Math.round(debugRect?.width ?? 0),
    }
  })
  assert(debugGrid.previewX < debugGrid.debugX && debugGrid.debugWidth >= 320, `Expected debug detail as rightmost fourth column: ${JSON.stringify(debugGrid)}`)
  assert(debugGrid.personaWidth >= grid.personaWidth - 2, `Debug column must not squeeze persona column: before=${JSON.stringify(grid)} after=${JSON.stringify(debugGrid)}`)
  assert(debugGrid.orchestrationWidth >= grid.orchestrationWidth - 2, `Debug column must not squeeze orchestration column: before=${JSON.stringify(grid)} after=${JSON.stringify(debugGrid)}`)
  assert(debugGrid.previewWidth >= grid.previewWidth - 2, `Debug column must not squeeze preview column: before=${JSON.stringify(grid)} after=${JSON.stringify(debugGrid)}`)
  assert(debugGrid.shellScrollWidth > debugGrid.shellClientWidth, `Expected horizontal scroll for four-column debug layout: ${JSON.stringify(debugGrid)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench coze lifecycle e2e')
} finally {
  await browser.close()
}
