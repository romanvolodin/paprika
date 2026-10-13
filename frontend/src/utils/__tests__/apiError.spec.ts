import { describe, expect, it } from 'vitest'
import { AxiosError } from 'axios'
import { firstValidationMessage } from '@/utils/apiError'

function axiosError(status: number, data: unknown) {
  return new AxiosError('failed', 'ERR_BAD_REQUEST', undefined, undefined, {
    status,
    data,
  } as never)
}

describe('firstValidationMessage', () => {
  it('returns the first message of a 400 validation response', () => {
    const error = axiosError(400, { detail: [{ msg: 'A shot with this name already exists.' }] })

    expect(firstValidationMessage(error)).toBe('A shot with this name already exists.')
  })

  it('returns null for other statuses, shapes and non-axios errors', () => {
    expect(firstValidationMessage(axiosError(403, { detail: 'nope' }))).toBeNull()
    expect(firstValidationMessage(axiosError(400, { detail: 'plain' }))).toBeNull()
    expect(firstValidationMessage(axiosError(400, { detail: [] }))).toBeNull()
    expect(firstValidationMessage(new Error('x'))).toBeNull()
  })
})
