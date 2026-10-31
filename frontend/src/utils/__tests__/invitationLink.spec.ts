import { afterEach, describe, expect, it, vi } from 'vitest'
import { copyToClipboard, invitationLink } from '@/utils/invitationLink'
import { formatExpiry } from '@/utils/format'

describe('invitationLink', () => {
  it('points at the invite page of this site', () => {
    expect(invitationLink('abc-123')).toBe(`${window.location.origin}/invite/abc-123`)
  })
})

describe('copyToClipboard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('puts the text on the clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { clipboard: { writeText } })

    const copied = await copyToClipboard('hello')

    expect(copied).toBe(true)
    expect(writeText).toHaveBeenCalledWith('hello')
  })

  it('says so when the browser refuses', async () => {
    vi.stubGlobal('navigator', {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
    })

    expect(await copyToClipboard('hello')).toBe(false)
  })

  it('says so when there is no clipboard at all', async () => {
    vi.stubGlobal('navigator', {})

    expect(await copyToClipboard('hello')).toBe(false)
  })
})

describe('formatExpiry', () => {
  it('says until which day', () => {
    expect(formatExpiry('2026-11-12T10:00:00Z')).toBe('до 12 ноября')
  })
})
