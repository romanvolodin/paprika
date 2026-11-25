import { computed } from 'vue'
import { useStorage } from '@vueuse/core'

export type ProjectStatusFilter = 'all' | 'active' | 'archived'

const FILTERS: ProjectStatusFilter[] = ['all', 'active', 'archived']

/**
 * The projects list can only be filtered by status on the client (the API
 * has no `is_active` query param), so the chosen filter is a pure UI
 * preference - persisted per list the same way `useViewMode` does it.
 */
export function useProjectStatusFilter(
  listKey: string,
  fallback: ProjectStatusFilter = 'all',
) {
  const stored = useStorage<string>(`paprika:project-status-filter:${listKey}`, fallback)

  return computed<ProjectStatusFilter>({
    get: () =>
      FILTERS.includes(stored.value as ProjectStatusFilter)
        ? (stored.value as ProjectStatusFilter)
        : fallback,
    set: (filter) => {
      stored.value = filter
    },
  })
}
