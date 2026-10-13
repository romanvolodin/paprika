import { describe, expect, it } from 'vitest'
import { formatFileSize, formatHours, formatVideoTiming } from '@/utils/format'

describe('formatFileSize', () => {
  it.each([
    [0, '0 Б'],
    [1023, '1023 Б'],
    [1024, '1 КБ'],
    [1536, '1,5 КБ'],
    [5 * 1024 * 1024, '5 МБ'],
    [2 * 1024 ** 3, '2 ГБ'],
  ])('%i bytes -> %s', (bytes, expected) => {
    expect(formatFileSize(bytes).replace(/\s/g, ' ')).toBe(expected)
  })
})

describe('formatVideoTiming', () => {
  it('shows frames and fps for a video', () => {
    expect(formatVideoTiming(240, 24)).toBe('240 к. · 24 fps')
  })

  it('trims a long fps fraction to three decimals', () => {
    expect(formatVideoTiming(100, 23.976023976)).toBe('100 к. · 23.976 fps')
  })

  it('shows a dash for an image', () => {
    expect(formatVideoTiming(null, null)).toBe('—')
  })
})

describe('formatHours', () => {
  it('shows estimated and actual hours', () => {
    expect(formatHours(8, 6.5).replace(/\s/g, ' ')).toBe('8 / 6,5')
  })

  it('shows a dash for an unset value', () => {
    expect(formatHours(null, null)).toBe('— / —')
    expect(formatHours(8, null)).toBe('8 / —')
  })
})
