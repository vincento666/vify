export function assertRuntime(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrapRuntimeResponse(response, label) {
  assertRuntime(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assertRuntime(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

function isTerminal(status) {
  return ['SUCCEEDED', 'FAILED', 'INTERRUPTED', 'CANCELLED'].includes(String(status || '').toUpperCase())
}

function runtimeResultUrl(baseUrl, started) {
  const resultRef = started.resultRef || started.runtimeRefs?.resultRef
  if (typeof resultRef === 'string' && resultRef) {
    return resultRef.startsWith('http') ? resultRef : `${baseUrl}${resultRef}`
  }
  assertRuntime(started.runId, `Runtime start missing runId/resultRef: ${JSON.stringify(started)}`)
  return `${baseUrl}/api/v1/runtime-runs/${started.runId}/result`
}

export async function waitForRuntimeResult(page, baseUrl, started, label, timeoutMs = 60000) {
  if (isTerminal(started.status) && started.output) return started

  const resultUrl = runtimeResultUrl(baseUrl, started)
  const deadline = Date.now() + timeoutMs
  let latest = started
  while (Date.now() < deadline) {
    latest = await unwrapRuntimeResponse(await page.request.get(resultUrl), `${label} result`)
    if (isTerminal(latest.status)) return latest
    await page.waitForTimeout(500)
  }
  throw new Error(`Timed out waiting for ${label} runtime result: ${JSON.stringify(latest)}`)
}
