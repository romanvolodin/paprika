import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { TaskNotPlacedError, useShotTasksStore } from '@/stores/shotTasks'
import * as tasksApi from '@/api/tasks'
import type { ShotTaskOut, TaskOut } from '@/types/api'

vi.mock('@/api/tasks')

const context = { shotId: 10, projectId: 1, companyId: 7 }

function buildTask(overrides: Partial<TaskOut> = {}): TaskOut {
  return {
    id: 100,
    project_id: 1,
    code: 'PRJ1',
    name: 'Sky replacement',
    description: '',
    type_id: 1,
    shot_ids: [10],
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function buildShotTask(overrides: Partial<ShotTaskOut> = {}): ShotTaskOut {
  return {
    id: 5,
    shot_id: 10,
    task: buildTask(),
    status_id: 2,
    assignee: null,
    estimated_hours: null,
    actual_hours: null,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function mockLoad(shotTasks: ShotTaskOut[]) {
  vi.mocked(tasksApi.listShotTasks).mockResolvedValue({ items: shotTasks })
  vi.mocked(tasksApi.listTaskTypes).mockResolvedValue({ items: [] })
  vi.mocked(tasksApi.listTaskStatuses).mockResolvedValue({ items: [] })
}

type ShotTaskList = Awaited<ReturnType<typeof tasksApi.listShotTasks>>

describe('useShotTasksStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('open loads the shot tasks together with the company task types and statuses', async () => {
    mockLoad([buildShotTask()])

    const store = useShotTasksStore()
    await store.open(context)

    expect(tasksApi.listShotTasks).toHaveBeenCalledWith(10)
    expect(tasksApi.listTaskTypes).toHaveBeenCalledWith(7)
    expect(tasksApi.listTaskStatuses).toHaveBeenCalledWith(7)
    expect(store.items).toHaveLength(1)
    expect(store.isLoading).toBe(false)
  })

  it('opening another shot clears the previous shot tasks right away', async () => {
    mockLoad([buildShotTask()])
    const store = useShotTasksStore()
    await store.open(context)

    let resolveSecond!: (value: ShotTaskList) => void
    vi.mocked(tasksApi.listShotTasks).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSecond = resolve
      }),
    )
    const pending = store.open({ ...context, shotId: 11 })

    expect(store.items).toEqual([])

    resolveSecond({ items: [buildShotTask({ id: 6, shot_id: 11 })] })
    await pending
    expect(store.items.map((item) => item.shot_id)).toEqual([11])
  })

  it('a slow response for an earlier shot does not overwrite the current one', async () => {
    let resolveFirst!: (value: ShotTaskList) => void
    vi.mocked(tasksApi.listShotTasks).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      }),
    )
    vi.mocked(tasksApi.listTaskTypes).mockResolvedValue({ items: [] })
    vi.mocked(tasksApi.listTaskStatuses).mockResolvedValue({ items: [] })
    const store = useShotTasksStore()
    const first = store.open(context)

    mockLoad([buildShotTask({ id: 6, shot_id: 11 })])
    await store.open({ ...context, shotId: 11 })

    resolveFirst({ items: [buildShotTask({ shot_id: 10 })] })
    await first

    expect(store.items.map((item) => item.shot_id)).toEqual([11])
    expect(store.isLoading).toBe(false)
  })

  it('addExisting places the task and refetches', async () => {
    mockLoad([buildShotTask()])
    vi.mocked(tasksApi.createShotTask).mockResolvedValue(buildShotTask())
    const store = useShotTasksStore()
    await store.open(context)
    vi.mocked(tasksApi.listShotTasks).mockClear()

    await store.addExisting(100)

    expect(tasksApi.createShotTask).toHaveBeenCalledWith(10, { task_id: 100 })
    expect(tasksApi.listShotTasks).toHaveBeenCalledTimes(1)
  })

  describe('createAndAdd', () => {
    it('creates the task in the project, places it on the shot and refetches', async () => {
      mockLoad([])
      vi.mocked(tasksApi.createTask).mockResolvedValue(buildTask({ id: 101 }))
      vi.mocked(tasksApi.createShotTask).mockResolvedValue(buildShotTask())
      const store = useShotTasksStore()
      await store.open(context)
      vi.mocked(tasksApi.listShotTasks).mockClear()

      await store.createAndAdd({ name: 'Roto', type_id: 3 })

      expect(tasksApi.createTask).toHaveBeenCalledWith(1, {
        name: 'Roto',
        type_id: 3,
        description: '',
      })
      expect(tasksApi.createShotTask).toHaveBeenCalledWith(10, { task_id: 101 })
      expect(tasksApi.listShotTasks).toHaveBeenCalledTimes(1)
    })

    it('does not place anything when creating the task fails', async () => {
      mockLoad([])
      vi.mocked(tasksApi.createTask).mockRejectedValue(new Error('invalid'))
      const store = useShotTasksStore()
      await store.open(context)

      await expect(store.createAndAdd({ name: 'Roto', type_id: 3 })).rejects.toThrow('invalid')
      expect(tasksApi.createShotTask).not.toHaveBeenCalled()
    })

    it('tells apart a task that was created but could not be placed', async () => {
      mockLoad([])
      vi.mocked(tasksApi.createTask).mockResolvedValue(buildTask({ id: 101 }))
      vi.mocked(tasksApi.createShotTask).mockRejectedValue(new Error('no default status'))
      const store = useShotTasksStore()
      await store.open(context)

      await expect(store.createAndAdd({ name: 'Roto', type_id: 3 })).rejects.toBeInstanceOf(
        TaskNotPlacedError,
      )
    })
  })

  it('update swaps in the server response without a refetch', async () => {
    mockLoad([buildShotTask({ id: 5 }), buildShotTask({ id: 6 })])
    vi.mocked(tasksApi.updateShotTask).mockResolvedValue(buildShotTask({ id: 5, status_id: 9 }))
    const store = useShotTasksStore()
    await store.open(context)
    vi.mocked(tasksApi.listShotTasks).mockClear()

    await store.update(5, { status_id: 9 })

    expect(tasksApi.updateShotTask).toHaveBeenCalledWith(5, { status_id: 9 })
    expect(store.items.map((item) => item.status_id)).toEqual([9, 2])
    expect(tasksApi.listShotTasks).not.toHaveBeenCalled()
  })

  it('a failed update leaves the list as it was', async () => {
    mockLoad([buildShotTask({ id: 5 })])
    vi.mocked(tasksApi.updateShotTask).mockRejectedValue(new Error('rejected'))
    const store = useShotTasksStore()
    await store.open(context)

    await expect(store.update(5, { status_id: 9 })).rejects.toThrow('rejected')
    expect(store.items[0]?.status_id).toBe(2)
  })

  it('remove deletes the shot task and refetches', async () => {
    mockLoad([])
    vi.mocked(tasksApi.deleteShotTask).mockResolvedValue(undefined as never)
    const store = useShotTasksStore()
    await store.open(context)
    vi.mocked(tasksApi.listShotTasks).mockClear()

    await store.remove(5)

    expect(tasksApi.deleteShotTask).toHaveBeenCalledWith(5)
    expect(tasksApi.listShotTasks).toHaveBeenCalledTimes(1)
  })
})
