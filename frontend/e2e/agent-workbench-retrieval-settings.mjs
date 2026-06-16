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
  const providers = await unwrap(await page.request.get(`${baseUrl}/api/v1/providers?page=1&pageSize=100`), 'list providers')
  for (const provider of providers.list ?? []) {
    if (!provider.enabled) continue
    if (String(provider.baseUrl || '').startsWith('mock://')) continue
    for (const model of provider.models ?? []) {
      if (model.enabled) return model.id
    }
  }
  throw new Error('No enabled model found for Agent retrieval settings e2e')
}

async function createKb(page, name) {
  return unwrap(
    await page.request.post(`${baseUrl}/api/v1/knowledge-bases`, {
      data: { name, description: 'retrieval settings e2e' },
    }),
    'create knowledge base',
  )
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const kb1 = await createKb(page, `Retrieval KB A ${Date.now()}`)
  const kb2 = await createKb(page, `Retrieval KB B ${Date.now()}`)
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Retrieval Settings Agent ${Date.now()}`,
        systemPrompt: 'Use retrieved knowledge.',
        modelConfigId,
        temperature: 0.2,
        maxTokens: 512,
        maxContextTurns: 4,
        knowledgeBaseId: kb1.id,
        knowledgeBaseIds: [kb1.id, kb2.id],
        retrievalSettings: {
          topK: 4,
          scoreThreshold: 0.5,
          rerank: true,
          citationStyle: 'numbered',
        },
        toolIds: [],
      },
    }),
    'create agent',
  )

  const detail = await unwrap(await page.request.get(`${baseUrl}/api/v1/agents/${agent.id}`), 'agent detail')
  assert(detail.knowledgeBaseIds.length === 2, 'agent detail should preserve multi knowledge base ids')
  assert(detail.retrievalSettings.topK === 4, 'agent detail should preserve topK')
  assert(detail.retrievalSettings.scoreThreshold === 0.5, 'agent detail should preserve threshold')

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'load' })
  const panel = page.getByTestId('agent-retrieval-settings')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByText('Top K').waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByText('Score 阈值').waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByText('引用格式').waitFor({ state: 'visible', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench retrieval settings e2e')
} finally {
  await browser.close()
}
