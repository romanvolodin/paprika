import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AxiosError } from 'axios'
import { useShotDetailStore } from '@/stores/shotDetail'
import * as projectsApi from '@/api/projects'
import * as shotsApi from '@/api/shots'
import type { CompanyOut, ProjectOut, ShotOut } from '@/types/api'

vi.mock('@/api/projects')
vi.mock('@/api/shots')

const company: CompanyOut = {
  id: 7,
  name: 'Acme',
  slug: 'acme',
  my_permissions: [],
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
    my_permissions: [],
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

function mockProjects(items: ProjectOut[]) {
  vi.mocked(projectsApi.listProjects).mockResolvedValue({
    items,
    total: items.length,
    page: 1,
    page_size: 1,
  })
}

function mockShotApi(shots: ShotOut[]) {
  vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({ items: [] })
  vi.mocked(shotsApi.listShots).mockResolvedValue({
    items: shots,
    total: shots.length,
    page: 1,
    page_size: 1,
  })
  vi.mocked(shotsApi.listShotStatuses).mockResolvedValue({ items: [] })
  vi.mocked(shotsApi.listShotGroups).mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 100,
  })
}

describe('useShotDetailStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('open resolves the project by code and the shot by exact name', async () => {
    mockProjects([buildProject()])
    mockShotApi([buildShot()])

    const store = useShotDetailStore()
    await store.open(company, 'PRJ', '0010')

    expect(projectsApi.listProjects).toHaveBeenCalledWith(7, { code: 'PRJ', page_size: 1 })
    expect(shotsApi.listShots).toHaveBeenCalledWith(1, { name: '0010', page_size: 1 })
    expect(store.project?.id).toBe(1)
    expect(store.shot?.name).toBe('0010')
    expect(store.state).toBe('ready')
  })

  it('open reports not-found when the project does not exist', async () => {
    mockProjects([])

    const store = useShotDetailStore()
    await store.open(company, 'PRJ', '0010')

    expect(store.state).toBe('not-found')
    expect(shotsApi.listShots).not.toHaveBeenCalled()
  })

  it('open reports not-found when the project has no shot with that name', async () => {
    mockProjects([buildProject()])
    mockShotApi([])

    const store = useShotDetailStore()
    await store.open(company, 'PRJ', '0010')

    expect(store.state).toBe('not-found')
    expect(store.shot).toBeNull()
  })

  it('open reports not-found when the API answers 404', async () => {
    mockProjects([buildProject()])
    mockShotApi([buildShot()])
    vi.mocked(shotsApi.listShots).mockRejectedValue(
      new AxiosError('Not found', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 404,
      } as never),
    )

    const store = useShotDetailStore()
    await store.open(company, 'PRJ', '0010')

    expect(store.state).toBe('not-found')
  })

  it('open reports an error for any other failure', async () => {
    vi.mocked(projectsApi.listProjects).mockRejectedValue(new Error('network'))

    const store = useShotDetailStore()
    await store.open(company, 'PRJ', '0010')

    expect(store.state).toBe('error')
  })

  it('a stale open does not overwrite the result of a newer one', async () => {
    let resolveFirst!: (value: Awaited<ReturnType<typeof projectsApi.listProjects>>) => void
    vi.mocked(projectsApi.listProjects).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      }),
    )
    mockShotApi([buildShot({ id: 11, name: '0020' })])

    const store = useShotDetailStore()
    const first = store.open(company, 'OLD', '0010')

    mockProjects([buildProject({ id: 5, code: 'NEW' })])
    await store.open(company, 'NEW', '0020')

    resolveFirst({ items: [buildProject({ id: 9, code: 'OLD' })], total: 1, page: 1, page_size: 1 })
    await first

    expect(store.project?.code).toBe('NEW')
    expect(store.shot?.name).toBe('0020')
    expect(store.state).toBe('ready')
  })

  it('updateShot replaces the shot with the server response', async () => {
    mockProjects([buildProject()])
    mockShotApi([buildShot()])
    vi.mocked(shotsApi.updateShot).mockResolvedValue(buildShot({ duration: 48 }))

    const store = useShotDetailStore()
    await store.open(company, 'PRJ', '0010')
    const input = { status_id: 3, group_ids: [], rec_timecode: null, duration: 48 }
    await store.updateShot(input)

    expect(shotsApi.updateShot).toHaveBeenCalledWith(10, input)
    expect(store.shot?.duration).toBe(48)
  })

  it('deleteShot deletes the open shot', async () => {
    mockProjects([buildProject()])
    mockShotApi([buildShot()])
    vi.mocked(shotsApi.deleteShot).mockResolvedValue(undefined as never)

    const store = useShotDetailStore()
    await store.open(company, 'PRJ', '0010')
    await store.deleteShot()

    expect(shotsApi.deleteShot).toHaveBeenCalledWith(10)
  })
})
