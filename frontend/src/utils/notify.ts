import { message } from 'ant-design-vue'

export interface NotifyOptions {
  duration?: number
}

export const notifySuccess = (content: string, options: NotifyOptions = {}) =>
  message.success(content, options.duration ?? 2.5)

export const notifyError = (content: string, options: NotifyOptions = {}) =>
  message.error(content, options.duration ?? 3.5)

export const notifyWarning = (content: string, options: NotifyOptions = {}) =>
  message.warning(content, options.duration ?? 3)
