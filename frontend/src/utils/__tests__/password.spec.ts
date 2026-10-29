import { describe, expect, it } from 'vitest'
import { generatePassword } from '@/utils/password'

describe('generatePassword', () => {
  it('makes a password of the asked length', () => {
    expect(generatePassword()).toHaveLength(14)
    expect(generatePassword(20)).toHaveLength(20)
  })

  it('leaves out the characters that are easy to confuse', () => {
    for (let i = 0; i < 50; i += 1) {
      expect(generatePassword(40)).not.toMatch(/[01OlIo]/)
    }
  })

  it('does not repeat itself', () => {
    expect(generatePassword()).not.toBe(generatePassword())
  })
})
