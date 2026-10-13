import { describe, expect, it } from 'vitest'
import { tagColor } from '@/utils/color'

describe('tagColor', () => {
  it('tints the fill and keeps the border and text solid', () => {
    expect(tagColor('#3366ff')).toEqual({
      color: '#3366ff26',
      borderColor: '#3366ff',
      textColor: '#3366ff',
    })
  })
})
