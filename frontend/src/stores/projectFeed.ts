import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import * as feedApi from '@/api/feed'
import type { FeedEventType, FeedItemOut, FeedQuery } from '@/types/api'

export type FeedScope = 'project' | 'mine'
export type FeedState = 'loading' | 'ready' | 'error'

export const FEED_EVENT_TYPES: FeedEventType[] = ['chat', 'version', 'task']

export const useProjectFeedStore = defineStore('projectFeed', () => {
  const state = ref<FeedState>('loading')
  const items = ref<FeedItemOut[]>([])
  const nextBeforeDate = ref<string | null>(null)
  const isLoadingMore = ref(false)
  const loadMoreFailed = ref(false)

  const scope = ref<FeedScope>('project')
  // Empty means every type.
  const types = ref<FeedEventType[]>([])

  const hasMore = computed(() => nextBeforeDate.value !== null)
  const isDefaultFilter = computed(() => scope.value === 'project' && types.value.length === 0)

  let projectId: number | null = null
  // A newer load invalidates any earlier one still in flight.
  let token = 0

  function query(beforeDate?: string): FeedQuery {
    return {
      mine: scope.value === 'mine' ? true : undefined,
      type: types.value.length > 0 ? types.value.join(',') : undefined,
      before_date: beforeDate,
    }
  }

  async function load() {
    if (projectId === null) return
    const myToken = ++token
    state.value = 'loading'
    isLoadingMore.value = false
    loadMoreFailed.value = false
    try {
      const result = await feedApi.listFeed(projectId, query())
      if (myToken !== token) return
      items.value = result.items
      nextBeforeDate.value = result.next_before_date
      state.value = 'ready'
    } catch {
      if (myToken !== token) return
      items.value = []
      nextBeforeDate.value = null
      state.value = 'error'
    }
  }

  async function loadMore() {
    if (projectId === null || nextBeforeDate.value === null || isLoadingMore.value) return
    const myToken = token
    isLoadingMore.value = true
    loadMoreFailed.value = false
    try {
      const result = await feedApi.listFeed(projectId, query(nextBeforeDate.value))
      if (myToken !== token) return
      items.value = [...items.value, ...result.items]
      nextBeforeDate.value = result.next_before_date
    } catch {
      if (myToken !== token) return
      loadMoreFailed.value = true
    } finally {
      if (myToken === token) isLoadingMore.value = false
    }
  }

  async function open(newProjectId: number) {
    projectId = newProjectId
    scope.value = 'project'
    types.value = []
    items.value = []
    nextBeforeDate.value = null
    await load()
  }

  async function setScope(value: FeedScope) {
    scope.value = value
    await load()
  }

  async function setTypes(value: FeedEventType[]) {
    // Every type chosen is the same as no filter.
    types.value =
      value.length === FEED_EVENT_TYPES.length
        ? []
        : FEED_EVENT_TYPES.filter((t) => value.includes(t))
    await load()
  }

  async function resetFilters() {
    scope.value = 'project'
    types.value = []
    await load()
  }

  return {
    state,
    items,
    hasMore,
    isLoadingMore,
    loadMoreFailed,
    scope,
    types,
    isDefaultFilter,
    open,
    loadMore,
    setScope,
    setTypes,
    resetFilters,
  }
})
