import { describe, expect, it } from 'vitest'
import { parseTimecode } from '@/utils/timecode'

describe('parseTimecode', () => {
  it('counts absolute frames from 00:00:00:00, hours included', () => {
    expect(parseTimecode('00:00:00:00', 25)).toBe(0)
    expect(parseTimecode('00:00:01:05', 25)).toBe(30)
    expect(parseTimecode('01:00:52:10', 25)).toBe(((1 * 60 + 0) * 60 + 52) * 25 + 10)
    expect(parseTimecode('08:01:35:12', 24)).toBe(((8 * 60 + 1) * 60 + 35) * 24 + 12)
  })

  it('accepts spaces as separators, including repeated ones', () => {
    expect(parseTimecode('01 00 52 10', 25)).toBe(parseTimecode('01:00:52:10', 25))
    expect(parseTimecode('10 26  02 02', 25)).toBe(parseTimecode('10:26:02:02', 25))
  })

  it('ignores spaces around the timecode', () => {
    expect(parseTimecode('  01:00:00:01 ', 25)).toBe(90001)
  })

  it.each(['', '01:00:52', '01:00:52:10:00', 'abc', '01:60:00:00', '01:00:60:00', '1:2:3:x'])(
    'rejects %j',
    (text) => {
      expect(parseTimecode(text, 25)).toBeNull()
    },
  )

  it('rejects a frame number that does not fit the fps', () => {
    expect(parseTimecode('00:00:00:24', 25)).toBe(24)
    expect(parseTimecode('00:00:00:25', 25)).toBeNull()
    expect(parseTimecode('00:00:00:24', 24)).toBeNull()
  })
})
