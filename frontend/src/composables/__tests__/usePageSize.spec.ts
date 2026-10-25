import { beforeEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, usePageSize } from '@/composables/usePageSize'

describe('usePageSize', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('starts with the default size when nothing is stored', () => {
    expect(usePageSize('shots').value).toBe(DEFAULT_PAGE_SIZE)
  })

  it('offers the default size among the options', () => {
    expect(PAGE_SIZE_OPTIONS).toContain(DEFAULT_PAGE_SIZE)
  })

  it('keeps the choice in localStorage under the list key', async () => {
    const size = usePageSize('shots')

    size.value = 200
    await nextTick()

    expect(localStorage.getItem('paprika:page-size:shots')).toBe('200')
    expect(usePageSize('shots').value).toBe(200)
  })

  it('remembers the choice separately for each list', async () => {
    usePageSize('shots').value = 200
    await nextTick()

    expect(usePageSize('projects').value).toBe(DEFAULT_PAGE_SIZE)
  })

  it('falls back when the stored size is not one of the options', () => {
    localStorage.setItem('paprika:page-size:shots', '7')

    expect(usePageSize('shots').value).toBe(DEFAULT_PAGE_SIZE)
  })

  it('falls back when the stored value is not a number', () => {
    localStorage.setItem('paprika:page-size:shots', 'many')

    expect(usePageSize('shots').value).toBe(DEFAULT_PAGE_SIZE)
  })
})
