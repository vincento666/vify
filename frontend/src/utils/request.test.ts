import { describe, expect, it } from 'vitest'

import { ApiError, toClientError, unwrapEnvelope } from './request'

describe('unwrapEnvelope', () => {
  it('returns data for a successful API envelope', () => {
    const data = unwrapEnvelope({
      code: 200,
      message: 'success',
      data: {
        status: 'UP',
      },
    })

    expect(data).toEqual({ status: 'UP' })
  })

  it('throws ApiError for an error envelope', () => {
    try {
      unwrapEnvelope({
        code: 404,
        message: 'Not Found',
        data: null,
      })
      throw new Error('expected unwrapEnvelope to throw')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).code).toBe(404)
      expect((error as ApiError).message).toBe('Not Found')
    }
  })

  it('extracts an API envelope from a non-2xx axios response', () => {
    const error = toClientError({
      isAxiosError: true,
      message: 'Request failed with status code 404',
      response: {
        data: {
          code: 404,
          message: 'Not Found',
          data: null,
        },
      },
    })

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).code).toBe(404)
    expect(error.message).toBe('Not Found')
  })
})
