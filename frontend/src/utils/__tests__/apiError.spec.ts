import { describe, expect, it } from 'vitest'
import { AxiosError } from 'axios'
import { describeVersionUploadError, firstValidationMessage } from '@/utils/apiError'

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

describe('describeVersionUploadError', () => {
  it('explains a duplicate version name', () => {
    expect(describeVersionUploadError(axiosError(409, {}))).toMatch(/уже есть/)
  })

  it('names the size limit the server reported on a 413', () => {
    const error = axiosError(413, {
      detail: [{ msg: 'The file is too large. Max size is 2048 MB.' }],
    })

    expect(describeVersionUploadError(error)).toContain('2048 МБ')
  })

  it('still explains a 413 without a readable limit', () => {
    expect(describeVersionUploadError(axiosError(413, {}))).toMatch(/слишком большой/)
  })

  it('points at the supported formats on a 400', () => {
    expect(describeVersionUploadError(axiosError(400, {}))).toMatch(/mp4/)
  })

  it('explains a missing permission', () => {
    expect(describeVersionUploadError(axiosError(403, {}))).toMatch(/нет прав/)
  })

  it('falls back to a generic message', () => {
    expect(describeVersionUploadError(axiosError(500, {}))).toBe('Не удалось загрузить версию.')
    expect(describeVersionUploadError(new Error('network'))).toBe('Не удалось загрузить версию.')
  })
})
