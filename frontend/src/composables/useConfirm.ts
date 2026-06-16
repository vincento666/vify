import { Modal } from 'ant-design-vue'
import { notifySuccess } from '@/utils/notify'

const confirmCancelledError = () =>
  Object.assign(new Error('confirm cancelled'), { code: 'CONFIRM_CANCELLED' })

function confirmWarning(content: string): Promise<void> {
  return new Promise((resolve, reject) => {
    Modal.confirm({
      title: '确认操作',
      content,
      okText: '确认',
      cancelText: '取消',
      onOk: () => {
        resolve()
      },
      onCancel: () => {
        reject(confirmCancelledError())
      },
    })
  })
}

export function useConfirm() {
  const confirm = async (
    message: string,
    apiFn: () => Promise<unknown>,
    successMsg = '操作成功'
  ): Promise<boolean> => {
    await confirmWarning(message)
    await apiFn()
    notifySuccess(successMsg)
    return true
  }

  return { confirm }
}
