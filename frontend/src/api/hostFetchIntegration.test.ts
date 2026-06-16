import { afterEach, describe, expect, it, vi } from 'vitest'

import { streamMessage } from './chat'
import { exportEvaluationRunCsv, importEvalCasesCsv } from './evaluation'
import { exportFaqCsv, importFaqCsv } from './knowledge'

describe('API functions using raw fetch', () => {
  afterEach(() => {
    delete globalThis.__HIFY_HOST__
    vi.unstubAllGlobals()
  })

  it('sends host headers for knowledge CSV import/export fetch calls', async () => {
    globalThis.__HIFY_HOST__ = {
      apiBaseUrl: 'https://host.example/api',
      actorId: 'knowledge-user',
      tenantId: 'tenant-k',
      requestId: 'req-k',
    }
    const fetchSpy = vi.fn(async (url: string, _init?: RequestInit) => {
      if (url.endsWith('/export-csv')) return new Response('question,answer\n', { status: 200 })
      return new Response(JSON.stringify({ code: 200, message: 'success', data: { imported: 1 } }), { status: 200 })
    })
    vi.stubGlobal('fetch', fetchSpy)

    await importFaqCsv(12, new Blob(['question,answer\nq,a\n']) as unknown as File)
    await exportFaqCsv(12)

    const [importUrl, importInit] = fetchSpy.mock.calls[0] as [string, RequestInit]
    const [exportUrl, exportInit] = fetchSpy.mock.calls[1] as [string, RequestInit]
    expect(importUrl).toBe('https://host.example/api/v1/knowledge-bases/12/faqs/import-csv')
    expect(importInit.headers).toMatchObject({
      'X-Hify-Actor-Id': 'knowledge-user',
      'X-Hify-Tenant-Id': 'tenant-k',
      'X-Request-Id': 'req-k',
    })
    expect(exportUrl).toBe('https://host.example/api/v1/knowledge-bases/12/faqs/export-csv')
    expect(exportInit.headers).toMatchObject({
      'X-Hify-Actor-Id': 'knowledge-user',
      'X-Hify-Tenant-Id': 'tenant-k',
    })
  })

  it('sends host headers for evaluation CSV import/export fetch calls', async () => {
    globalThis.__HIFY_HOST__ = {
      apiBaseUrl: 'https://host.example/api',
      actorId: 'eval-user',
      tenantId: 'tenant-e',
      requestId: 'req-e',
    }
    const fetchSpy = vi.fn(async (url: string, _init?: RequestInit) => {
      if (url.endsWith('/export-csv')) return new Response('status,input\n', { status: 200 })
      return new Response(JSON.stringify({ code: 200, message: 'success', data: { createdCount: 1 } }), { status: 200 })
    })
    vi.stubGlobal('fetch', fetchSpy)

    await importEvalCasesCsv(9, new Blob(['input,expectedOutput\nhello,hello\n']) as unknown as File)
    await exportEvaluationRunCsv(88)

    const [importUrl, importInit] = fetchSpy.mock.calls[0] as [string, RequestInit]
    const [exportUrl, exportInit] = fetchSpy.mock.calls[1] as [string, RequestInit]
    expect(importUrl).toBe('https://host.example/api/v1/eval-sets/9/cases/import-csv')
    expect(importInit.headers).toMatchObject({
      'X-Hify-Actor-Id': 'eval-user',
      'X-Hify-Tenant-Id': 'tenant-e',
      'X-Request-Id': 'req-e',
    })
    expect(exportUrl).toBe('https://host.example/api/v1/evaluation-runs/88/export-csv')
    expect(exportInit.headers).toMatchObject({
      'X-Hify-Actor-Id': 'eval-user',
      'X-Hify-Tenant-Id': 'tenant-e',
    })
  })

  it('sends host headers for chat streaming fetch calls', async () => {
    globalThis.__HIFY_HOST__ = {
      apiBaseUrl: 'https://host.example/api',
      actorId: 'chat-user',
      tenantId: 'tenant-c',
      requestId: 'req-c',
    }
    const done = new Promise<void>((resolve, reject) => {
      const fetchSpy = vi.fn(async (_url: string, _init?: RequestInit) => new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode('data: {"type":"done","finishReason":"stop","latencyMs":5}\n\n'))
            controller.close()
          },
        }),
        { status: 200 },
      ))
      vi.stubGlobal('fetch', fetchSpy)
      streamMessage(
        77,
        'hello',
        () => {},
        () => {
          try {
            const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
            expect(url).toBe('https://host.example/api/v1/chat/sessions/77/messages')
            expect(init.headers).toMatchObject({
              'Content-Type': 'application/json',
              Accept: 'text/event-stream',
              'X-Hify-Actor-Id': 'chat-user',
              'X-Hify-Tenant-Id': 'tenant-c',
              'X-Request-Id': 'req-c',
            })
            resolve()
          } catch (error) {
            reject(error)
          }
        },
        reject,
      )
    })

    await done
  })
})
