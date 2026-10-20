import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as tasksApi from '@/api/tasks'
import type { TaskOut, TaskTypeOut } from '@/types/api'

export const useProjectTasksStore = defineStore('projectTasks', () => {
  const items = ref<TaskOut[]>([])
  const types = ref<TaskTypeOut[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const search = ref('')
  const typeId = ref<number | null>(null)
  const isLoading = ref(false)

  let projectId: number | null = null
  let fetchToken = 0

  async function fetchTasks() {
    if (projectId === null) return
    const token = ++fetchToken
    isLoading.value = true
    try {
      const result = await tasksApi.listTasks(projectId, {
        page: page.value,
        page_size: pageSize.value,
        search: search.value || undefined,
        type: typeId.value ?? undefined,
      })
      if (token !== fetchToken) return
      items.value = result.items
      total.value = result.total
      page.value = result.page
      pageSize.value = result.page_size
    } finally {
      if (token === fetchToken) isLoading.value = false
    }
  }

  async function open(newProjectId: number, companyId: number) {
    projectId = newProjectId
    items.value = []
    total.value = 0
    page.value = 1
    search.value = ''
    typeId.value = null

    const [typeList] = await Promise.all([tasksApi.listTaskTypes(companyId), fetchTasks()])
    if (projectId !== newProjectId) return
    types.value = typeList.items
  }

  async function setSearch(value: string) {
    search.value = value
    page.value = 1
    await fetchTasks()
  }

  async function setType(value: number | null) {
    typeId.value = value
    page.value = 1
    await fetchTasks()
  }

  async function setPage(value: number) {
    page.value = value
    await fetchTasks()
  }

  return {
    items,
    types,
    total,
    page,
    pageSize,
    search,
    typeId,
    isLoading,
    open,
    setSearch,
    setType,
    setPage,
  }
})
