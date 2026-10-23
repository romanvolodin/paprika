import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AxiosError } from 'axios'
import { useShotsStore } from '@/stores/shots'
import * as projectsApi from '@/api/projects'
import * as shotsApi from '@/api/shots'
import type {
  CompanyOut,
  ProjectMemberOut,
  ProjectOut,
  ShotFiltersOut,
  ShotOut,
  ShotStatusOut,
} from '@/types/api'

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

function buildStatus(id: number, name: string): ShotStatusOut {
  return {
    id,
    company_id: 7,
    name,
    color: '#336699',
    order: id,
    is_default: false,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  } as ShotStatusOut
}

function buildMember(userId: number, firstName: string, lastName: string): ProjectMemberOut {
  return {
    id: userId * 100,
    user_id: userId,
    email: `user${userId}@example.com`,
    first_name: firstName,
    last_name: lastName,
    avatar: null,
    role: 'artist',
  } as ProjectMemberOut
}

function mockFilters(filters: Partial<ShotFiltersOut> = {}) {
  vi.mocked(shotsApi.getShotFilters).mockResolvedValue({
    status_ids: [],
    assignee_ids: [],
    has_unassigned: false,
    ...filters,
  })
}

function mockShotData() {
  mockFilters()
  vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({ items: [] })
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

  it('createShot posts to the open project and refetches the list', async () => {
    mockProjectLookup([buildProject()])
    mockShotData()
    vi.mocked(shotsApi.createShot).mockResolvedValue(buildShot({ id: 99, name: '0099' }))

    const store = useShotsStore()
    await store.open(company, 'PRJ')
    vi.mocked(shotsApi.listShots).mockClear()
    const input = { name: '0099', status_id: 3, group_ids: [], rec_timecode: null, duration: null }
    const created = await store.createShot(input)

    expect(shotsApi.createShot).toHaveBeenCalledWith(1, input)
    expect(created?.id).toBe(99)
    expect(shotsApi.listShots).toHaveBeenCalledTimes(1)
  })

  it('createShot keeps the error and does not refetch when the API rejects', async () => {
    mockProjectLookup([buildProject()])
    mockShotData()
    vi.mocked(shotsApi.createShot).mockRejectedValue(new Error('duplicate'))

    const store = useShotsStore()
    await store.open(company, 'PRJ')
    vi.mocked(shotsApi.listShots).mockClear()

    await expect(
      store.createShot({
        name: '0010',
        status_id: 3,
        group_ids: [],
        rec_timecode: null,
        duration: null,
      }),
    ).rejects.toThrow('duplicate')
    expect(shotsApi.listShots).not.toHaveBeenCalled()
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

  describe('filters', () => {
    async function openWithFilters() {
      mockProjectLookup([buildProject()])
      mockShotData()
      mockFilters({ status_ids: [2, 3, 5], assignee_ids: [11, 12], has_unassigned: true })
      vi.mocked(shotsApi.listShotStatuses).mockResolvedValue({
        items: [
          buildStatus(1, 'Не начат'),
          buildStatus(2, 'В работе'),
          buildStatus(3, 'Готов'),
          buildStatus(5, 'Отмена'),
        ],
      })
      vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({
        items: [
          buildMember(11, 'Коля', 'Зайцев'),
          buildMember(12, 'Костя', 'Соломонов'),
          buildMember(13, 'Роман', 'Володин'),
        ],
      })
      const store = useShotsStore()
      await store.open(company, 'PRJ')
      return store
    }

    function lastQuery() {
      return vi.mocked(shotsApi.listShots).mock.lastCall![1]
    }

    it('offers only the statuses and assignees that occur in the project', async () => {
      const store = await openWithFilters()

      expect(store.statusOptions.map((status) => status.name)).toEqual([
        'В работе',
        'Готов',
        'Отмена',
      ])
      expect(store.assigneeOptions).toEqual([
        { value: 'none', label: 'Не назначен' },
        { value: 11, label: 'Коля Зайцев' },
        { value: 12, label: 'Костя Соломонов' },
      ])
    })

    it('does not offer "Не назначен" when every task has an assignee', async () => {
      mockProjectLookup([buildProject()])
      mockShotData()
      mockFilters({ assignee_ids: [11], has_unassigned: false })
      vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({
        items: [buildMember(11, 'Коля', 'Зайцев')],
      })
      const store = useShotsStore()
      await store.open(company, 'PRJ')

      expect(store.assigneeOptions.map((option) => option.value)).toEqual([11])
    })

    it('sends no filter parameters while nothing is ticked', async () => {
      await openWithFilters()

      expect(lastQuery()).toEqual({ page: 1, page_size: 20 })
    })

    it('sends the ticked statuses and goes back to the first page', async () => {
      const store = await openWithFilters()
      await store.setPage(3)
      await store.setStatusFilter([2, 3], false)

      expect(store.page).toBe(1)
      expect(lastQuery()).toMatchObject({ page: 1, status: '2,3' })
    })

    it('sends the ticked assignees, "none" included', async () => {
      const store = await openWithFilters()
      await store.setAssigneeFilter(['none', 11], false)

      expect(lastQuery()).toMatchObject({ assigned_to: 'none,11' })
    })

    it('sends both filters together with the search', async () => {
      const store = await openWithFilters()
      await store.setSearch('00')
      await store.setStatusFilter([3], false)
      await store.setAssigneeFilter([12], false)

      expect(lastQuery()).toEqual({
        page: 1,
        page_size: 20,
        search: '00',
        status: '3',
        assigned_to: '12',
      })
    })

    it('an inverted status filter sends every other offered status', async () => {
      const store = await openWithFilters()
      await store.setStatusFilter([3], true)

      expect(lastQuery()).toMatchObject({ status: '2,5' })
    })

    it('an inverted assignee filter sends every other offered value', async () => {
      const store = await openWithFilters()
      await store.setAssigneeFilter([11], true)

      expect(lastQuery()).toMatchObject({ assigned_to: 'none,12' })
    })

    it('inverting a filter that has everything ticked shows nothing without asking the server', async () => {
      const store = await openWithFilters()
      await store.setStatusFilter([2, 3, 5], false)
      vi.mocked(shotsApi.listShots).mockClear()
      await store.setStatusFilter([2, 3, 5], true)

      expect(shotsApi.listShots).not.toHaveBeenCalled()
      expect(store.items).toEqual([])
      expect(store.total).toBe(0)
    })

    it('inverting with nothing ticked does nothing', async () => {
      const store = await openWithFilters()
      await store.setStatusFilter([], true)

      expect(store.statusInverted).toBe(false)
      expect(lastQuery()).toEqual({ page: 1, page_size: 20 })
    })

    it('resetting a filter removes it from the request', async () => {
      const store = await openWithFilters()
      await store.setStatusFilter([3], true)
      await store.setStatusFilter([], false)

      expect(store.statusSelected).toEqual([])
      expect(store.statusInverted).toBe(false)
      expect(lastQuery()).toEqual({ page: 1, page_size: 20 })
    })

    it('open forgets the filters left over from a previous visit', async () => {
      const store = await openWithFilters()
      await store.setStatusFilter([3], true)
      await store.setAssigneeFilter([11], true)
      await store.open(company, 'PRJ')

      expect(store.statusSelected).toEqual([])
      expect(store.statusInverted).toBe(false)
      expect(store.assigneeSelected).toEqual([])
      expect(store.assigneeInverted).toBe(false)
      expect(lastQuery()).toEqual({ page: 1, page_size: 20 })
    })

    it('createShot refreshes the offered values and drops a ticked one that disappeared', async () => {
      const store = await openWithFilters()
      await store.setStatusFilter([5], false)
      vi.mocked(shotsApi.createShot).mockResolvedValue(buildShot({ id: 99 }))
      mockFilters({ status_ids: [1, 2, 3], assignee_ids: [11, 12], has_unassigned: true })
      await store.createShot({
        name: '0099',
        status_id: 1,
        group_ids: [],
        rec_timecode: null,
        duration: null,
      })

      expect(store.statusOptions.map((status) => status.id)).toEqual([1, 2, 3])
      expect(store.statusSelected).toEqual([])
      expect(lastQuery()).toEqual({ page: 1, page_size: 20 })
    })

    it('a slower, older answer does not overwrite a newer one', async () => {
      const store = await openWithFilters()
      let resolveSlow!: (value: Awaited<ReturnType<typeof shotsApi.listShots>>) => void
      vi.mocked(shotsApi.listShots).mockReturnValueOnce(
        new Promise((resolve) => {
          resolveSlow = resolve
        }),
      )
      const slow = store.setStatusFilter([2], false)
      vi.mocked(shotsApi.listShots).mockResolvedValueOnce({
        items: [buildShot({ id: 2 })],
        total: 1,
        page: 1,
        page_size: 20,
      })
      await store.setStatusFilter([3], false)
      resolveSlow({
        items: [buildShot({ id: 1 }), buildShot({ id: 4 })],
        total: 2,
        page: 1,
        page_size: 20,
      })
      await slow

      expect(store.items.map((shot) => shot.id)).toEqual([2])
    })
  })
})
