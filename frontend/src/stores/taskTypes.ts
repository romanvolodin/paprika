import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as tasksApi from '@/api/tasks'
import type { TaskTypeCreateIn, TaskTypeOut, TaskTypeUpdateIn } from '@/types/api'

export const useTaskTypesStore = defineStore('taskTypes', () => {
  const items = ref<TaskTypeOut[]>([])
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
      const result = await tasksApi.listTaskTypes(companyId)
      if (token !== fetchToken) return
      items.value = result.items
    } finally {
      if (token === fetchToken) isLoading.value = false
    }
  }

  async function create(companyId: number, input: TaskTypeCreateIn) {
    await tasksApi.createTaskType(companyId, input)
    await fetch(companyId)
  }

  async function update(companyId: number, taskTypeId: number, input: TaskTypeUpdateIn) {
    await tasksApi.updateTaskType(taskTypeId, input)
    await fetch(companyId)
  }

  async function remove(companyId: number, taskTypeId: number) {
    await tasksApi.deleteTaskType(taskTypeId)
    await fetch(companyId)
  }

  return { items, isLoading, fetch, create, update, remove }
})
