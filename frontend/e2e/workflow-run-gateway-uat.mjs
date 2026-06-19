import { mkdir, writeFile } from 'node:fs/promises'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const artifactDir =
  process.env.HIFY_E2E_ARTIFACT_DIR || 'artifacts/slices/199-workflow-run-gateway/199.1'
const screenshotPath =
  process.env.HIFY_E2E_SCREENSHOT || `${artifactDir}/screenshots/workflow-run-gateway.png`

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  if (!response.ok()) {
    const text = await response.text()
    throw new Error(`${label} HTTP ${response.status()}: ${text}`)
  }
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function waitForRuntime(page, resultRef, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs
  let latest = null
  while (Date.now() < deadline) {
    latest = await unwrap(await page.request.get(`${baseUrl}${resultRef}`), `runtime result ${resultRef}`)
    if (['SUCCEEDED', 'FAILED', 'INTERRUPTED', 'CANCELLED'].includes(latest.status)) return latest
    await page.waitForTimeout(150)
  }
  throw new Error(`Timed out waiting for runtime result ${resultRef}; latest=${JSON.stringify(latest)}`)
}

function parseSseDataFrame(text) {
  const dataLines = text
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice('data:'.length).trim())
  assert(dataLines.length > 0, `Expected SSE data frame, got ${text}`)
  return JSON.parse(dataLines.join('\n'))
}

async function main() {
  await mkdir(`${artifactDir}/screenshots`, { recursive: true })
  const browser = await chromium.launch({ headless: process.env.HIFY_E2E_HEADED !== '1' })
  const context = await browser.newContext({ viewport: { width: 1440, height: 980 } })
  const page = await context.newPage()
  const stamp = Date.now()
  const idempotencyKey = `workflow-gateway-uat-${stamp}`

  try {
    await page.goto(baseUrl, { waitUntil: 'domcontentloaded' })

    const workflow = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/workflows`, {
        data: {
          name: `Workflow Run Gateway UAT ${stamp}`,
          description: 'workflow run gateway browser UAT',
          nodes: [
            { nodeKey: 'start', type: 'START', name: 'Start', config: {} },
            {
              nodeKey: 'message_1',
              type: 'MESSAGE',
              name: 'Message',
              config: { content: `gateway ok ${stamp}`, outputVariable: 'content' },
            },
            {
              nodeKey: 'end',
              type: 'END',
              name: 'End',
              config: { outputVariable: 'final', output: '{{message_1.content}}' },
            },
          ],
          edges: [
            { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
            { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
          ],
        },
      }),
      'create workflow',
    )
    const version = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/publish`),
      'publish workflow',
    )
    const started = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
        data: {
          input: { 'sys.query': `gateway ${stamp}` },
          versionId: version.id,
          idempotencyKey,
        },
      }),
      'start workflow run gateway',
    )
    const replay = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
        data: {
          input: { 'sys.query': `gateway ${stamp}` },
          versionId: version.id,
          idempotencyKey,
        },
      }),
      'replay workflow run gateway',
    )
    const terminal = await waitForRuntime(page, started.resultRef)
    const events = await unwrap(await page.request.get(`${baseUrl}${started.eventsRef}`), 'list runtime events')
    const nodes = await unwrap(await page.request.get(`${baseUrl}${started.nodesRef}`), 'list runtime nodes')
    const streamResponse = await page.request.post(
      `${baseUrl}/api/v1/workflows/${workflow.id}/runs:stream?_testLimit=1`,
      {
        data: {
          input: { 'sys.query': `stream ${stamp}` },
          idempotencyKey: `${idempotencyKey}-stream`,
        },
      },
    )
    assert(streamResponse.ok(), `stream gateway HTTP ${streamResponse.status()}: ${await streamResponse.text()}`)
    const streamEvent = parseSseDataFrame(await streamResponse.text())

    assert(started.ownerType === 'WORKFLOW', `ownerType should be WORKFLOW, got ${started.ownerType}`)
    assert(started.ownerId === workflow.id, `ownerId should match workflow id, got ${started.ownerId}`)
    assert(started.workflowId === workflow.id, `workflowId should match workflow id, got ${started.workflowId}`)
    assert(started.versionId === version.id, `versionId should match publish version, got ${started.versionId}`)
    assert(started.statusRef === `/api/v1/runtime-runs/${started.runId}`, 'statusRef should target runtime run')
    assert(started.resultRef === `/api/v1/runtime-runs/${started.runId}/result`, 'resultRef should target runtime result')
    assert(replay.runId === started.runId, 'idempotent replay should return the original run')
    assert(replay.idempotentReplay === true, 'idempotent replay flag should be true')
    assert(terminal.status === 'SUCCEEDED', `runtime should succeed, got ${JSON.stringify(terminal)}`)
    assert(terminal.output?.final === `gateway ok ${stamp}`, `runtime output mismatch: ${JSON.stringify(terminal)}`)
    assert(events.list.some((event) => event.type === 'workflow_run_started'), 'started event should be persisted')
    assert(nodes.list.length === 2, `expected two executable node rows, got ${nodes.list.length}`)
    assert(streamEvent.type === 'workflow_run_started', `stream should start with started event, got ${streamEvent.type}`)
    assert(streamEvent.payload?.ownerId === workflow.id, `stream ownerId mismatch: ${JSON.stringify(streamEvent)}`)
    assert(
      streamEvent.payload?.resultRef?.startsWith('/api/v1/runtime-runs/'),
      `stream should expose resultRef, got ${JSON.stringify(streamEvent)}`,
    )

    await page.screenshot({ path: screenshotPath, fullPage: true })
    await writeFile(
      `${artifactDir}/uat.json`,
      JSON.stringify(
        {
          workflowId: workflow.id,
          versionId: version.id,
          runId: started.runId,
          status: terminal.status,
          output: terminal.output,
          replayRunId: replay.runId,
          events: events.list.map((event) => event.type),
          nodeStatuses: nodes.list.map((node) => [node.nodeKey, node.status]),
          streamType: streamEvent.type,
          screenshotPath,
        },
        null,
        2,
      ),
    )
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
