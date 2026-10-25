import { beforeEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import { useViewMode } from '@/composables/useViewMode'

describe('useViewMode', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('starts as a table when nothing is stored', () => {
    expect(useViewMode('shots').value).toBe('table')
  })

  it('starts as the given fallback when nothing is stored', () => {
    expect(useViewMode('shots', 'cards').value).toBe('cards')
  })

  it('keeps the choice in localStorage under the list key', async () => {
    const mode = useViewMode('shots')

    mode.value = 'cards'
    await nextTick()

    expect(localStorage.getItem('paprika:view-mode:shots')).toBe('cards')
    expect(useViewMode('shots').value).toBe('cards')
  })

  it('remembers the choice separately for each list', async () => {
    useViewMode('shots').value = 'cards'
    await nextTick()

    expect(useViewMode('projects').value).toBe('table')
  })

  it('falls back when the stored value is not a known mode', () => {
    localStorage.setItem('paprika:view-mode:shots', 'gallery')

    expect(useViewMode('shots').value).toBe('table')
  })
})
