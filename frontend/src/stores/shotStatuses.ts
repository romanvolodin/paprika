import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as shotsApi from '@/api/shots'
import type { ShotStatusCreateIn, ShotStatusOut, ShotStatusUpdateIn } from '@/types/api'

export const useShotStatusesStore = defineStore('shotStatuses', () => {
  const items = ref<ShotStatusOut[]>([])
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
      const result = await shotsApi.listShotStatuses(companyId)
      if (token !== fetchToken) return
      items.value = result.items
    } finally {
      if (token === fetchToken) isLoading.value = false
    }
  }

  async function create(companyId: number, input: ShotStatusCreateIn) {
    await shotsApi.createShotStatus(companyId, input)
    await fetch(companyId)
  }

  // Setting a status as the default unsets the previous one on the
  // server, so the whole list is refetched rather than patched locally.
  async function update(companyId: number, statusId: number, input: ShotStatusUpdateIn) {
    await shotsApi.updateShotStatus(statusId, input)
    await fetch(companyId)
  }

  async function remove(companyId: number, statusId: number) {
    await shotsApi.deleteShotStatus(statusId)
    await fetch(companyId)
  }

  return { items, isLoading, fetch, create, update, remove }
})
