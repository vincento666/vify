import axios from 'axios'
import { ElMessage } from 'element-plus'

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

export class ApiError extends Error {
  code: number
  data: unknown

  constructor(code: number, message: string, data: unknown) {
    super(message || '请求失败')
    this.name = 'ApiError'
    this.code = code
    this.data = data
  }
}

export function unwrapEnvelope<T>(payload: ApiEnvelope<T>): T {
  if (!payload || typeof payload.code !== 'number') {
    throw new ApiError(500, 'Invalid API response', payload)
  }
  if (payload.code !== 200) {
    throw new ApiError(payload.code, payload.message, payload.data)
  }
  return payload.data
}

export function toClientError(error: unknown): Error {
  if (axios.isAxiosError(error) && error.response?.data) {
    try {
      unwrapEnvelope(error.response.data as ApiEnvelope<unknown>)
    } catch (apiError) {
      if (apiError instanceof Error) return apiError
    }
  }
  if (error instanceof Error) return error
  return new Error('网络异常')
}

const instance = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

instance.interceptors.response.use(
  (response) => {
    try {
      return unwrapEnvelope(response.data)
    } catch (error) {
      const message = error instanceof Error ? error.message : '请求失败'
      ElMessage.error(message)
      return Promise.reject(error)
    }
  },
  (error) => {
    const clientError = toClientError(error)
    ElMessage.error(clientError.message || '网络异常')
    return Promise.reject(clientError)
  }
)

export const get = <T>(url: string, params?: object): Promise<T> =>
  instance.get(url, { params })

export const post = <T>(url: string, data?: object): Promise<T> =>
  instance.post(url, data)

export const put = <T>(url: string, data?: object): Promise<T> =>
  instance.put(url, data)

export const del = <T>(url: string): Promise<T> =>
  instance.delete(url)
