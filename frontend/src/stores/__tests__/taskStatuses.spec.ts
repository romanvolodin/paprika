import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTaskStatusesStore } from '@/stores/taskStatuses'
import * as tasksApi from '@/api/tasks'
import type { TaskStatusOut } from '@/types/api'

vi.mock('@/api/tasks')

function buildStatus(overrides: Partial<TaskStatusOut> = {}): TaskStatusOut {
  return {
    id: 1,
    company_id: 7,
    name: 'In progress',
    color: '#3366ff',
    order: 1,
    is_default: false,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

type StatusList = Awaited<ReturnType<typeof tasksApi.listTaskStatuses>>

function mockList(items: TaskStatusOut[]) {
  vi.mocked(tasksApi.listTaskStatuses).mockResolvedValue({ items })
}

describe('useTaskStatusesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetch loads the company task statuses', async () => {
    mockList([buildStatus()])

    const store = useTaskStatusesStore()
    await store.fetch(7)

    expect(tasksApi.listTaskStatuses).toHaveBeenCalledWith(7)
    expect(store.items).toHaveLength(1)
    expect(store.isLoading).toBe(false)
  })

  it('create posts the input and refetches', async () => {
    mockList([buildStatus(), buildStatus({ id: 2, name: 'Review' })])
    vi.mocked(tasksApi.createTaskStatus).mockResolvedValue(buildStatus({ id: 2 }))

    const store = useTaskStatusesStore()
    const input = { name: 'Review', color: '#aabbcc', order: null, is_default: false }
    await store.create(7, input)

    expect(tasksApi.createTaskStatus).toHaveBeenCalledWith(7, input)
    expect(store.items).toHaveLength(2)
  })

  it('update refetches the whole list so a moved default is picked up', async () => {
    mockList([
      buildStatus({ id: 1, is_default: false }),
      buildStatus({ id: 2, name: 'New', is_default: true }),
    ])
    vi.mocked(tasksApi.updateTaskStatus).mockResolvedValue(buildStatus({ id: 2 }))

    const store = useTaskStatusesStore()
    const input = { name: 'New', color: '#3366ff', order: 1, is_default: true }
    await store.update(7, 2, input)

    expect(tasksApi.updateTaskStatus).toHaveBeenCalledWith(2, input)
    expect(store.items.map((status) => status.is_default)).toEqual([false, true])
  })

  it('remove deletes the status and refetches', async () => {
    mockList([])
    vi.mocked(tasksApi.deleteTaskStatus).mockResolvedValue(undefined as never)

    const store = useTaskStatusesStore()
    await store.remove(7, 1)

    expect(tasksApi.deleteTaskStatus).toHaveBeenCalledWith(1)
    expect(store.items).toEqual([])
  })

  it('a failed delete does not refetch', async () => {
    vi.mocked(tasksApi.deleteTaskStatus).mockRejectedValue(new Error('in use'))

    const store = useTaskStatusesStore()

    await expect(store.remove(7, 1)).rejects.toThrow('in use')
    expect(tasksApi.listTaskStatuses).not.toHaveBeenCalled()
  })

  it('fetching another company clears the previous company statuses right away', async () => {
    mockList([buildStatus({ company_id: 7 })])
    const store = useTaskStatusesStore()
    await store.fetch(7)

    let resolveSecond!: (value: StatusList) => void
    vi.mocked(tasksApi.listTaskStatuses).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSecond = resolve
      }),
    )
    const pending = store.fetch(8)

    expect(store.items).toEqual([])

    resolveSecond({ items: [buildStatus({ id: 2, company_id: 8 })] })
    await pending
    expect(store.items.map((status) => status.company_id)).toEqual([8])
  })

  it('a slow response for an earlier company does not overwrite the current one', async () => {
    let resolveFirst!: (value: StatusList) => void
    vi.mocked(tasksApi.listTaskStatuses).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      }),
    )
    const store = useTaskStatusesStore()
    const first = store.fetch(7)

    mockList([buildStatus({ id: 2, company_id: 8 })])
    await store.fetch(8)

    resolveFirst({ items: [buildStatus({ company_id: 7 })] })
    await first

    expect(store.items.map((status) => status.company_id)).toEqual([8])
    expect(store.isLoading).toBe(false)
  })
})
