// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { readFileSync } from 'node:fs'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { dirname, resolve } from 'node:path'
// @ts-expect-error Vitest runs this contract test in Node; app tsconfig does not ship node types.
import { fileURLToPath } from 'node:url'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const antMocks = vi.hoisted(() => ({
  message: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
  Modal: {
    confirm: vi.fn(),
  },
}))

vi.mock('ant-design-vue', () => antMocks)

import { useConfirm } from '@/composables/useConfirm'
import { notifyError, notifySuccess, notifyWarning } from '@/utils/notify'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')

function readProjectFile(path: string) {
  return readFileSync(resolve(projectRoot, path), 'utf8')
}

describe('Ant Design Vue feedback migration', () => {
  beforeEach(() => {
    antMocks.message.success.mockReset()
    antMocks.message.error.mockReset()
    antMocks.message.warning.mockReset()
    antMocks.Modal.confirm.mockReset()
  })

  it('keeps cross-cutting feedback code off shared UI adapters and Element Plus', () => {
    const files = [
      'src/utils/notify.ts',
      'src/utils/request.ts',
      'src/composables/useConfirm.ts',
    ]

    const matches = files.flatMap((file) => {
      const content = readProjectFile(file)
      return [
        ...Array.from(content.matchAll(/@\/shared\/ui/g), () => `${file} -> @/shared/ui`),
        ...Array.from(content.matchAll(/element-plus/g), () => `${file} -> element-plus`),
      ]
    })

    expect(matches).toEqual([])
  })

  it('maps notify helpers to Ant Design Vue message with stable durations', () => {
    notifySuccess('saved')
    notifyError('failed')
    notifyWarning('check')

    expect(antMocks.message.success).toHaveBeenCalledWith('saved', 2.5)
    expect(antMocks.message.error).toHaveBeenCalledWith('failed', 3.5)
    expect(antMocks.message.warning).toHaveBeenCalledWith('check', 3)
  })

  it('runs confirmed actions and keeps cancellation as a rejected promise', async () => {
    const apiFn = vi.fn().mockResolvedValue(undefined)
    const confirmed = useConfirm().confirm('Delete item?', apiFn, 'done')
    const config = antMocks.Modal.confirm.mock.calls[0][0]

    expect(config).toMatchObject({
      title: '确认操作',
      content: 'Delete item?',
      okText: '确认',
      cancelText: '取消',
    })

    config.onOk()

    await expect(confirmed).resolves.toBe(true)
    expect(apiFn).toHaveBeenCalledTimes(1)
    expect(antMocks.message.success).toHaveBeenCalledWith('done', 2.5)

    const cancelledApiFn = vi.fn()
    const cancelled = useConfirm().confirm('Delete item?', cancelledApiFn)
    antMocks.Modal.confirm.mock.calls[1][0].onCancel()

    await expect(cancelled).rejects.toMatchObject({ code: 'CONFIRM_CANCELLED' })
    expect(cancelledApiFn).not.toHaveBeenCalled()
  })
})
