import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AxiosError } from 'axios'
import { useShotsStore } from '@/stores/shots'
import * as projectsApi from '@/api/projects'
import * as shotsApi from '@/api/shots'
import type { CompanyOut, ProjectOut, ShotOut } from '@/types/api'

vi.mock('@/api/projects')
vi.mock('@/api/shots')

const company: CompanyOut = {
  id: 7,
  name: 'Acme',
  slug: 'acme',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

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
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function buildShot(overrides: Partial<ShotOut> = {}): ShotOut {
  return {
    id: 10,
    project_id: 1,
    group_ids: [],
    status_id: 3,
    name: '0010',
    rec_timecode: null,
    duration: null,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function mockProjectLookup(items: ProjectOut[]) {
  vi.mocked(projectsApi.listProjects).mockResolvedValue({
    items,
    total: items.length,
    page: 1,
    page_size: 100,
  })
}

function mockShotData() {
  vi.mocked(shotsApi.listShotStatuses).mockResolvedValue({ items: [] })
  vi.mocked(shotsApi.listShotGroups).mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 100,
  })
  vi.mocked(shotsApi.listShots).mockResolvedValue({
    items: [buildShot()],
    total: 1,
    page: 1,
    page_size: 20,
  })
}

describe('useShotsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('open looks the project up by its exact code', async () => {
    mockProjectLookup([buildProject({ id: 1, code: 'PRJ' })])
    mockShotData()

    const store = useShotsStore()
    await store.open(company, 'PRJ')

    expect(projectsApi.listProjects).toHaveBeenCalledWith(7, { code: 'PRJ', page_size: 1 })
    expect(store.project?.id).toBe(1)
    expect(shotsApi.listShots).toHaveBeenCalledWith(1, {
      page: 1,
      page_size: 20,
      search: undefined,
    })
    expect(store.items).toHaveLength(1)
    expect(store.state).toBe('ready')
  })

  it('open reports not-found when no project has that code', async () => {
    mockProjectLookup([])

    const store = useShotsStore()
    await store.open(company, 'PRJ')

    expect(store.state).toBe('not-found')
    expect(store.project).toBeNull()
    expect(shotsApi.listShots).not.toHaveBeenCalled()
  })

  it('open reports not-found when the API answers 404', async () => {
    mockProjectLookup([buildProject()])
    mockShotData()
    vi.mocked(shotsApi.listShots).mockRejectedValue(
      new AxiosError('Not found', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 404,
      } as never),
    )

    const store = useShotsStore()
    await store.open(company, 'PRJ')

    expect(store.state).toBe('not-found')
  })

  it('open reports an error for any other failure', async () => {
    vi.mocked(projectsApi.listProjects).mockRejectedValue(new Error('network'))

    const store = useShotsStore()
    await store.open(company, 'PRJ')

    expect(store.state).toBe('error')
  })

  it('open resets search and page left over from a previous project', async () => {
    mockProjectLookup([buildProject()])
    mockShotData()

    const store = useShotsStore()
    await store.open(company, 'PRJ')
    await store.setSearch('00')
    await store.setPage(3)
    await store.open(company, 'PRJ')

    expect(store.search).toBe('')
    expect(vi.mocked(shotsApi.listShots).mock.lastCall).toEqual([
      1,
      { page: 1, page_size: 20, search: undefined },
    ])
  })

  it('setSearch goes back to the first page and refetches with the query', async () => {
    mockProjectLookup([buildProject()])
    mockShotData()

    const store = useShotsStore()
    await store.open(company, 'PRJ')
    await store.setPage(2)
    await store.setSearch('00')

    expect(store.page).toBe(1)
    expect(vi.mocked(shotsApi.listShots).mock.lastCall).toEqual([
      1,
      { page: 1, page_size: 20, search: '00' },
    ])
  })

  it('a stale open does not overwrite the result of a newer one', async () => {
    let resolveFirst!: (value: Awaited<ReturnType<typeof projectsApi.listProjects>>) => void
    vi.mocked(projectsApi.listProjects).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      }),
    )
    mockShotData()

    const store = useShotsStore()
    const first = store.open(company, 'OLD')

    mockProjectLookup([buildProject({ id: 5, code: 'NEW' })])
    await store.open(company, 'NEW')

    resolveFirst({
      items: [buildProject({ id: 9, code: 'OLD' })],
      total: 1,
      page: 1,
      page_size: 100,
    })
    await first

    expect(store.project?.code).toBe('NEW')
    expect(store.state).toBe('ready')
  })
})
