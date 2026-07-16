import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/host/request', () => ({
  buildHostHeaders: () => ({ 'X-Hify-Test': '1' }),
  resolveApiUrl: (path: string) => `http://hify.test${path}`,
}))

describe('runtime-lab SOP message stream', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('reconnects a POST stream from the durable cursor and closes its controller', async () => {
    vi.useFakeTimers()
    const received: Array<Record<string, unknown>> = []
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(closedSseResponse(
        sseFrame({ type: 'delta', source: 'runtime_lab', payload: { reply: '正在路由' } })
        + sseFrame({ type: 'delta', source: 'provider', sequence: 4, delta: '正在核验' }),
      ))
      .mockResolvedValueOnce(closedSseResponse(
        sseFrame({
          type: 'done',
          source: 'runtime_v2',
          sequence: 5,
          event: { type: 'workflow_run_interrupted', payload: { output: { interrupt: { question: '请确认' } } } },
        }),
      ))
    vi.stubGlobal('fetch', fetchMock)

    const { openRuntimeLabSopMessageStream } = await import('./runtimeLabSopEventStream')
    const stream = openRuntimeLabSopMessageStream(7, {
      message: '我要退票',
      idempotencyKey: 'front-stream-1',
    }, {
      reconnectDelayMs: 10,
      onFrame: (frame) => received.push(frame as unknown as Record<string, unknown>),
    })

    await vi.waitFor(() => expect(received).toHaveLength(2))
    await vi.advanceTimersByTimeAsync(10)
    await stream.done
    stream.close()

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      'http://hify.test/v1/runtime-lab/sessions/7/messages:stream?afterSequence=0',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ message: '我要退票', idempotencyKey: 'front-stream-1' }),
        headers: expect.objectContaining({ Accept: 'text/event-stream', 'Content-Type': 'application/json' }),
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      'http://hify.test/v1/runtime-lab/sessions/7/messages:stream?afterSequence=4',
      expect.any(Object),
    )
    expect(received.map((frame) => frame.sequence).filter(Boolean)).toEqual([4, 5])
    expect(stream.lastSequence()).toBe(5)
  })

  it('reports that a live frame was received before reconnect exhaustion', async () => {
    vi.useFakeTimers()
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(closedSseResponse(
        sseFrame({ type: 'delta', source: 'runtime_lab', payload: { reply: '正在路由' } }),
      ))
      .mockRejectedValue(new Error('connection dropped'))
    vi.stubGlobal('fetch', fetchMock)

    const { openRuntimeLabSopMessageStream } = await import('./runtimeLabSopEventStream')
    const stream = openRuntimeLabSopMessageStream(7, {
      message: '我要退票',
      idempotencyKey: 'front-stream-disconnect',
    }, {
      reconnectDelayMs: 10,
      maxReconnects: 0,
      onFrame: () => {},
    })

    await expect(stream.done).rejects.toThrow('RuntimeLab SOP stream')

    expect(stream.hasReceivedFrame()).toBe(true)
  })
})

function sseFrame(frame: Record<string, unknown>) {
  return `data: ${JSON.stringify(frame)}\n\n`
}

function closedSseResponse(frames: string) {
  const encoder = new TextEncoder()
  return {
    ok: true,
    body: new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(frames))
        controller.close()
      },
    }),
  } as Response
}
