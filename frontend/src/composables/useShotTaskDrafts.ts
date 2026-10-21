import { computed, reactive, ref, watch, type Ref } from 'vue'
import { useShotTasksStore } from '@/stores/shotTasks'
import type { ShotTaskOut, ShotTaskUpdateIn } from '@/types/api'

export interface TaskDraft {
  status_id: number
  actual_hours: number | null
}

interface Context {
  shotId: number
  projectId: number
  companyId: number
}

/**
 * The shot's tasks with edits that are kept on the page and saved only
 * when asked (the upload page saves them after the version is up).
 * Rows that were not touched are never sent.
 */
export function useShotTaskDrafts(context: Ref<Context>) {
  const store = useShotTasksStore()
  const drafts = reactive<Record<number, TaskDraft>>({})
  const loadFailed = ref(false)

  watch(
    context,
    async (next) => {
      loadFailed.value = false
      try {
        await store.open(next)
      } catch {
        loadFailed.value = true
      }
    },
    { immediate: true },
  )

  function fromItem(item: ShotTaskOut): TaskDraft {
    return { status_id: item.status_id, actual_hours: item.actual_hours }
  }

  // A new row gets a draft; a row that went away loses its one. A draft
  // already being edited is left alone when the list is refreshed.
  watch(
    () => store.items,
    (items) => {
      const ids = new Set(items.map((item) => item.id))
      for (const key of Object.keys(drafts)) {
        if (!ids.has(Number(key))) delete drafts[Number(key)]
      }
      for (const item of items) {
        if (!(item.id in drafts)) drafts[item.id] = fromItem(item)
      }
    },
    { immediate: true },
  )

  const rows = computed(() =>
    store.items.flatMap((item) => (drafts[item.id] ? [{ item, draft: drafts[item.id] }] : [])),
  )

  // Statuses of the main workflow first (by order), side statuses after.
  const statusOptions = computed(() =>
    [...store.statuses]
      .sort((a, b) => (a.order ?? Infinity) - (b.order ?? Infinity))
      .map((status) => ({ label: status.name, value: status.id })),
  )

  const changedRows = computed(() =>
    rows.value.filter(
      ({ item, draft }) =>
        draft.status_id !== item.status_id || draft.actual_hours !== item.actual_hours,
    ),
  )

  function setStatus(shotTaskId: number, statusId: number) {
    if (drafts[shotTaskId]) drafts[shotTaskId].status_id = statusId
  }

  function setHours(shotTaskId: number, hours: number | null) {
    if (drafts[shotTaskId]) drafts[shotTaskId].actual_hours = hours
  }

  /**
   * Saves the changed rows one by one (so the chat gets the events in
   * order). Returns false if any of them failed; the failed ones stay
   * changed and can be saved again.
   */
  async function saveChanged(): Promise<boolean> {
    let allSaved = true
    for (const { item, draft } of changedRows.value) {
      const input: ShotTaskUpdateIn = {}
      if (draft.status_id !== item.status_id) input.status_id = draft.status_id
      if (draft.actual_hours !== item.actual_hours) input.actual_hours = draft.actual_hours
      try {
        await store.update(item.id, input)
        const saved = store.items.find((candidate) => candidate.id === item.id)
        if (saved) drafts[item.id] = fromItem(saved)
      } catch {
        allSaved = false
      }
    }
    return allSaved
  }

  return {
    rows,
    statusOptions,
    changedRows,
    loading: computed(() => store.isLoading),
    loadFailed,
    setStatus,
    setHours,
    saveChanged,
  }
}
