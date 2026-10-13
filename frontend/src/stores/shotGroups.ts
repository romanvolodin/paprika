import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as shotsApi from '@/api/shots'
import type { ShotGroupOut } from '@/types/api'

const MAX_PAGE_SIZE = 100

export const useShotGroupsStore = defineStore('shotGroups', () => {
  const items = ref<ShotGroupOut[]>([])
  const isLoading = ref(false)

  // The store is shared by every project page, so a response for a
  // project the user already left must not overwrite the current one.
  let loadedProjectId: number | null = null
  let fetchToken = 0

  async function fetch(projectId: number) {
    const token = ++fetchToken
    if (loadedProjectId !== projectId) {
      items.value = []
      loadedProjectId = projectId
    }
    isLoading.value = true
    try {
      const result = await shotsApi.listShotGroups(projectId, { page_size: MAX_PAGE_SIZE })
      if (token !== fetchToken) return
      items.value = result.items
    } finally {
      if (token === fetchToken) isLoading.value = false
    }
  }

  async function create(projectId: number, name: string) {
    await shotsApi.createShotGroup(projectId, { name })
    await fetch(projectId)
  }

  async function rename(projectId: number, groupId: number, name: string) {
    await shotsApi.renameShotGroup(groupId, { name })
    await fetch(projectId)
  }

  async function remove(projectId: number, groupId: number) {
    await shotsApi.deleteShotGroup(groupId)
    await fetch(projectId)
  }

  return { items, isLoading, fetch, create, rename, remove }
})
