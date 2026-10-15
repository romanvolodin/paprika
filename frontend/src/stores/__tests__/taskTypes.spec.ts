import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTaskTypesStore } from '@/stores/taskTypes'
import * as tasksApi from '@/api/tasks'
import type { TaskTypeOut } from '@/types/api'

vi.mock('@/api/tasks')

function buildType(overrides: Partial<TaskTypeOut> = {}): TaskTypeOut {
  return {
    id: 1,
    company_id: 7,
    name: 'Cleanup',
    abbreviation: 'CLN',
    color: '#3366ff',
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

type TypeList = Awaited<ReturnType<typeof tasksApi.listTaskTypes>>

function mockList(items: TaskTypeOut[]) {
  vi.mocked(tasksApi.listTaskTypes).mockResolvedValue({ items })
}

describe('useTaskTypesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetch loads the company task types', async () => {
    mockList([buildType()])

    const store = useTaskTypesStore()
    await store.fetch(7)

    expect(tasksApi.listTaskTypes).toHaveBeenCalledWith(7)
    expect(store.items).toHaveLength(1)
    expect(store.isLoading).toBe(false)
  })

  it('create posts the input and refetches', async () => {
    mockList([buildType(), buildType({ id: 2, name: 'Roto', abbreviation: 'RTO' })])
    vi.mocked(tasksApi.createTaskType).mockResolvedValue(buildType({ id: 2 }))

    const store = useTaskTypesStore()
    const input = { name: 'Roto', abbreviation: 'RTO', color: '#aabbcc' }
    await store.create(7, input)

    expect(tasksApi.createTaskType).toHaveBeenCalledWith(7, input)
    expect(store.items).toHaveLength(2)
  })

  it('update patches the type and refetches', async () => {
    mockList([buildType({ name: 'Renamed' })])
    vi.mocked(tasksApi.updateTaskType).mockResolvedValue(buildType({ name: 'Renamed' }))

    const store = useTaskTypesStore()
    await store.update(7, 1, { name: 'Renamed' })

    expect(tasksApi.updateTaskType).toHaveBeenCalledWith(1, { name: 'Renamed' })
    expect(store.items[0]?.name).toBe('Renamed')
  })

  it('remove deletes the type and refetches', async () => {
    mockList([])
    vi.mocked(tasksApi.deleteTaskType).mockResolvedValue(undefined as never)

    const store = useTaskTypesStore()
    await store.remove(7, 1)

    expect(tasksApi.deleteTaskType).toHaveBeenCalledWith(1)
    expect(store.items).toEqual([])
  })

  it('a failed create does not refetch', async () => {
    vi.mocked(tasksApi.createTaskType).mockRejectedValue(new Error('duplicate'))

    const store = useTaskTypesStore()

    await expect(
      store.create(7, { name: 'Cleanup', abbreviation: 'CLN', color: '#3366ff' }),
    ).rejects.toThrow('duplicate')
    expect(tasksApi.listTaskTypes).not.toHaveBeenCalled()
  })

  it('fetching another company clears the previous company types right away', async () => {
    mockList([buildType({ company_id: 7 })])
    const store = useTaskTypesStore()
    await store.fetch(7)

    let resolveSecond!: (value: TypeList) => void
    vi.mocked(tasksApi.listTaskTypes).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSecond = resolve
      }),
    )
    const pending = store.fetch(8)

    expect(store.items).toEqual([])

    resolveSecond({ items: [buildType({ id: 2, company_id: 8 })] })
    await pending
    expect(store.items.map((type) => type.company_id)).toEqual([8])
  })

  it('a slow response for an earlier company does not overwrite the current one', async () => {
    let resolveFirst!: (value: TypeList) => void
    vi.mocked(tasksApi.listTaskTypes).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      }),
    )
    const store = useTaskTypesStore()
    const first = store.fetch(7)

    mockList([buildType({ id: 2, company_id: 8 })])
    await store.fetch(8)

    resolveFirst({ items: [buildType({ company_id: 7 })] })
    await first

    expect(store.items.map((type) => type.company_id)).toEqual([8])
    expect(store.isLoading).toBe(false)
  })
})
