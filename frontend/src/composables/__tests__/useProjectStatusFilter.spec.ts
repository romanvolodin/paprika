import { beforeEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import { useProjectStatusFilter } from '@/composables/useProjectStatusFilter'

describe('useProjectStatusFilter', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('defaults to showing every project', () => {
    expect(useProjectStatusFilter('projects').value).toBe('all')
  })

  it('keeps the choice in localStorage under the list key', async () => {
    const filter = useProjectStatusFilter('projects')

    filter.value = 'archived'
    await nextTick()

    expect(localStorage.getItem('paprika:project-status-filter:projects')).toBe('archived')
    expect(useProjectStatusFilter('projects').value).toBe('archived')
  })

  it('remembers the choice separately for each list', async () => {
    useProjectStatusFilter('projects').value = 'active'
    await nextTick()

    expect(useProjectStatusFilter('archive').value).toBe('all')
  })

  it('falls back when the stored value is not a known filter', () => {
    localStorage.setItem('paprika:project-status-filter:projects', 'deleted')

    expect(useProjectStatusFilter('projects').value).toBe('all')
  })
})
