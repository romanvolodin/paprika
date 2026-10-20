import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectTasksStore } from '@/stores/projectTasks'
import * as tasksApi from '@/api/tasks'
import type { TaskOut, TaskTypeOut } from '@/types/api'

vi.mock('@/api/tasks')

function buildTask(overrides: Partial<TaskOut> = {}): TaskOut {
  return {
    id: 1,
    project_id: 1,
    code: 'CLN4821',
    name: 'Clean up wires',
    description: '',
    type_id: 3,
    shot_ids: [10, 11],
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function buildType(overrides: Partial<TaskTypeOut> = {}): TaskTypeOut {
  return {
    id: 3,
    company_id: 7,
    name: 'Клинап',
    abbreviation: 'CLN',
    color: '#ff5733',
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function pageOf(items: TaskOut[], overrides: Record<string, number> = {}) {
  return { items, total: items.length, page: 1, page_size: 20, ...overrides }
}

describe('useProjectTasksStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(tasksApi.listTasks).mockResolvedValue(pageOf([buildTask()]))
    vi.mocked(tasksApi.listTaskTypes).mockResolvedValue({ items: [buildType()] })
  })

  it('open loads the first page of the project tasks and the company task types', async () => {
    const store = useProjectTasksStore()

    await store.open(1, 7)

    expect(tasksApi.listTasks).toHaveBeenCalledWith(1, {
      page: 1,
      page_size: 20,
      search: undefined,
      type: undefined,
    })
    expect(tasksApi.listTaskTypes).toHaveBeenCalledWith(7)
    expect(store.items).toHaveLength(1)
    expect(store.types).toHaveLength(1)
    expect(store.total).toBe(1)
    expect(store.isLoading).toBe(false)
  })

  it('open resets the search, type filter and page left from another project', async () => {
    const store = useProjectTasksStore()
    await store.open(1, 7)
    await store.setSearch('wire')
    await store.setType(3)

    await store.open(2, 7)

    expect(store.search).toBe('')
    expect(store.typeId).toBeNull()
    expect(store.page).toBe(1)
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith(2, {
      page: 1,
      page_size: 20,
      search: undefined,
      type: undefined,
    })
  })

  it('setSearch goes back to the first page and refetches with the search', async () => {
    const store = useProjectTasksStore()
    await store.open(1, 7)
    await store.setPage(3)

    await store.setSearch('wire')

    expect(tasksApi.listTasks).toHaveBeenLastCalledWith(1, {
      page: 1,
      page_size: 20,
      search: 'wire',
      type: undefined,
    })
  })

  it('setType filters by the type and clearing it removes the filter', async () => {
    const store = useProjectTasksStore()
    await store.open(1, 7)

    await store.setType(3)
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith(1, {
      page: 1,
      page_size: 20,
      search: undefined,
      type: 3,
    })

    await store.setType(null)
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith(1, {
      page: 1,
      page_size: 20,
      search: undefined,
      type: undefined,
    })
  })

  it('setPage refetches the requested page keeping the filters', async () => {
    const store = useProjectTasksStore()
    await store.open(1, 7)
    await store.setType(3)

    await store.setPage(2)

    expect(tasksApi.listTasks).toHaveBeenLastCalledWith(1, {
      page: 2,
      page_size: 20,
      search: undefined,
      type: 3,
    })
  })

  it('a slow response for an old filter does not overwrite the newer one', async () => {
    const store = useProjectTasksStore()
    await store.open(1, 7)

    let resolveOld!: (value: ReturnType<typeof pageOf>) => void
    vi.mocked(tasksApi.listTasks)
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveOld = resolve
        }),
      )
      .mockResolvedValueOnce(pageOf([buildTask({ id: 2, name: 'Newer' })]))

    const old = store.setSearch('a')
    await store.setSearch('ab')
    resolveOld(pageOf([buildTask({ id: 1, name: 'Older' })]))
    await old

    expect(store.items[0]?.name).toBe('Newer')
  })
})
