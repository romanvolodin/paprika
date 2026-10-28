import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectsStore } from '@/stores/projects'
import * as projectsApi from '@/api/projects'
import type { ProjectOut } from '@/types/api'

vi.mock('@/api/projects')

function buildProject(overrides: Partial<ProjectOut> = {}): ProjectOut {
  return {
    id: 1,
    company_id: 7,
    name: 'Feature Film',
    code: 'PRJ',
    description: '',
    cover: null,
    start_date: null,
    deadline: null,
    is_active: true,
    my_permissions: [],
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('useProjectsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchProjects loads a page for the given company and mirrors pagination back', async () => {
    vi.mocked(projectsApi.listProjects).mockResolvedValue({
      items: [buildProject()],
      total: 1,
      page: 1,
      page_size: 20,
    })

    const store = useProjectsStore()
    await store.fetchProjects(7)

    expect(projectsApi.listProjects).toHaveBeenCalledWith(7, {
      page: 1,
      page_size: 20,
      search: undefined,
    })
    expect(store.items).toHaveLength(1)
    expect(store.total).toBe(1)
    expect(store.isLoading).toBe(false)
  })

  it('sets isLoading while a fetch is in flight', async () => {
    let resolveFetch!: (value: Awaited<ReturnType<typeof projectsApi.listProjects>>) => void
    vi.mocked(projectsApi.listProjects).mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve
      }),
    )

    const store = useProjectsStore()
    const pending = store.fetchProjects(7)
    expect(store.isLoading).toBe(true)

    resolveFetch({ items: [], total: 0, page: 1, page_size: 20 })
    await pending

    expect(store.isLoading).toBe(false)
  })

  it('setSearch resets to page 1 and refetches the same company with the search term', async () => {
    vi.mocked(projectsApi.listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    })

    const store = useProjectsStore()
    await store.fetchProjects(7)
    store.page = 3

    await store.setSearch('feature')

    expect(store.search).toBe('feature')
    expect(projectsApi.listProjects).toHaveBeenLastCalledWith(7, {
      page: 1,
      page_size: 20,
      search: 'feature',
    })
  })

  it('setPage refetches the same company with the requested page', async () => {
    vi.mocked(projectsApi.listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 2,
      page_size: 20,
    })

    const store = useProjectsStore()
    await store.fetchProjects(7)

    await store.setPage(2)

    expect(projectsApi.listProjects).toHaveBeenLastCalledWith(7, {
      page: 2,
      page_size: 20,
      search: undefined,
    })
  })

  it('switching to a different company refetches scoped to the new one', async () => {
    vi.mocked(projectsApi.listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    })

    const store = useProjectsStore()
    await store.fetchProjects(7)
    await store.fetchProjects(9)
    await store.setPage(2)

    expect(projectsApi.listProjects).toHaveBeenLastCalledWith(9, {
      page: 2,
      page_size: 20,
      search: undefined,
    })
  })
})
