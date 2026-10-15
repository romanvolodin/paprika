import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as tasksApi from '@/api/tasks'
import type { TaskStatusCreateIn, TaskStatusOut, TaskStatusUpdateIn } from '@/types/api'

export const useTaskStatusesStore = defineStore('taskStatuses', () => {
  const items = ref<TaskStatusOut[]>([])
  const isLoading = ref(false)

  // The store is shared by every company page, so a response for a
  // company the user already left must not overwrite the current one.
  let loadedCompanyId: number | null = null
  let fetchToken = 0

  async function fetch(companyId: number) {
    const token = ++fetchToken
    if (loadedCompanyId !== companyId) {
      items.value = []
      loadedCompanyId = companyId
    }
    isLoading.value = true
    try {
      const result = await tasksApi.listTaskStatuses(companyId)
      if (token !== fetchToken) return
      items.value = result.items
    } finally {
      if (token === fetchToken) isLoading.value = false
    }
  }

  async function create(companyId: number, input: TaskStatusCreateIn) {
    await tasksApi.createTaskStatus(companyId, input)
    await fetch(companyId)
  }

  // Setting a status as the default unsets the previous one on the
  // server, so the whole list is refetched rather than patched locally.
  async function update(companyId: number, taskStatusId: number, input: TaskStatusUpdateIn) {
    await tasksApi.updateTaskStatus(taskStatusId, input)
    await fetch(companyId)
  }

  async function remove(companyId: number, taskStatusId: number) {
    await tasksApi.deleteTaskStatus(taskStatusId)
    await fetch(companyId)
  }

  return { items, isLoading, fetch, create, update, remove }
})
