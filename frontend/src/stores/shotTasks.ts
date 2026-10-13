import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as tasksApi from '@/api/tasks'
import type { ShotTaskOut, ShotTaskUpdateIn, TaskStatusOut, TaskTypeOut } from '@/types/api'

/**
 * Thrown by `createAndAdd` when the new task was created but putting it
 * on the shot failed: the task now exists in the project and can be
 * placed on the shot later from the "existing task" list.
 */
export class TaskNotPlacedError extends Error {
  readonly cause: unknown

  constructor(cause: unknown) {
    super('The task was created but could not be placed on the shot.')
    this.name = 'TaskNotPlacedError'
    this.cause = cause
  }
}

interface Context {
  shotId: number
  projectId: number
  companyId: number
}

export const useShotTasksStore = defineStore('shotTasks', () => {
  const items = ref<ShotTaskOut[]>([])
  const types = ref<TaskTypeOut[]>([])
  const statuses = ref<TaskStatusOut[]>([])
  const isLoading = ref(false)

  // The store is shared by every shot page, so it remembers which shot
  // it was opened for and ignores responses for one the user left.
  let context: Context | null = null
  let fetchToken = 0

  async function refetch() {
    if (!context) return
    const { shotId, companyId } = context
    const token = ++fetchToken
    isLoading.value = true
    try {
      const [shotTasks, typeList, statusList] = await Promise.all([
        tasksApi.listShotTasks(shotId),
        tasksApi.listTaskTypes(companyId),
        tasksApi.listTaskStatuses(companyId),
      ])
      if (token !== fetchToken) return
      items.value = shotTasks.items
      types.value = typeList.items
      statuses.value = statusList.items
    } finally {
      if (token === fetchToken) isLoading.value = false
    }
  }

  async function open(next: Context) {
    const sameShot = context?.shotId === next.shotId && context?.companyId === next.companyId
    context = next
    if (!sameShot) {
      items.value = []
      types.value = []
      statuses.value = []
    }
    await refetch()
  }

  async function addExisting(taskId: number) {
    if (!context) return
    await tasksApi.createShotTask(context.shotId, { task_id: taskId })
    await refetch()
  }

  async function createAndAdd(input: { name: string; type_id: number }) {
    if (!context) return
    const task = await tasksApi.createTask(context.projectId, { ...input, description: '' })
    try {
      await tasksApi.createShotTask(context.shotId, { task_id: task.id })
    } catch (error) {
      throw new TaskNotPlacedError(error)
    }
    await refetch()
  }

  async function update(shotTaskId: number, input: ShotTaskUpdateIn) {
    const updated = await tasksApi.updateShotTask(shotTaskId, input)
    items.value = items.value.map((item) => (item.id === updated.id ? updated : item))
  }

  async function remove(shotTaskId: number) {
    await tasksApi.deleteShotTask(shotTaskId)
    await refetch()
  }

  return { items, types, statuses, isLoading, open, addExisting, createAndAdd, update, remove }
})
