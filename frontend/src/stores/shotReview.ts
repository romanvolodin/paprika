import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as versionsApi from '@/api/versions'
import type { VersionOut } from '@/types/api'

export type ShotReviewState = 'loading' | 'ready' | 'empty' | 'not-found' | 'error'

const MAX_PAGE_SIZE = 100

/**
 * What the "Просмотр" tab shows: the shot's latest versions and the one
 * being played. The played version is picked by name (it comes from the
 * `?version=` part of the address); with no name it is the newest one.
 */
export const useShotReviewStore = defineStore('shotReview', () => {
  const state = ref<ShotReviewState>('loading')
  const versions = ref<VersionOut[]>([])
  const current = ref<VersionOut | null>(null)

  let loadedShotId: number | null = null
  // More versions exist than were loaded, so an older one may have to
  // be looked up by name.
  let hasMore = false
  // A newer call invalidates any earlier one still in flight.
  let token = 0

  async function resolve(shotId: number, name: string | null, myToken: number) {
    if (name === null) {
      current.value = versions.value[0] ?? null
      state.value = current.value ? 'ready' : 'empty'
      return
    }

    let found = versions.value.find((version) => version.name === name)
    if (!found && hasMore) {
      const result = await versionsApi.listVersions(shotId, {
        search: name,
        page_size: MAX_PAGE_SIZE,
      })
      if (myToken !== token) return
      found = result.items.find((version) => version.name === name)
    }
    current.value = found ?? null
    state.value = found ? 'ready' : 'not-found'
  }

  /** Load the shot's versions anew, then pick the one to play. */
  async function load(shotId: number, name: string | null) {
    const myToken = ++token
    state.value = 'loading'
    current.value = null
    if (loadedShotId !== shotId) versions.value = []

    try {
      const result = await versionsApi.listVersions(shotId, { page_size: MAX_PAGE_SIZE })
      if (myToken !== token) return
      versions.value = result.items
      hasMore = result.total > result.items.length
      loadedShotId = shotId
      await resolve(shotId, name, myToken)
    } catch {
      if (myToken !== token) return
      state.value = 'error'
    }
  }

  /** Pick another version of the already loaded shot. */
  async function select(shotId: number, name: string | null) {
    if (loadedShotId !== shotId) return load(shotId, name)
    const myToken = ++token
    try {
      await resolve(shotId, name, myToken)
    } catch {
      if (myToken !== token) return
      state.value = 'error'
    }
  }

  return { state, versions, current, load, select }
})
