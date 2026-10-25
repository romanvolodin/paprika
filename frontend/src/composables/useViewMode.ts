import { computed } from 'vue'
import { useStorage } from '@vueuse/core'

export type ViewMode = 'table' | 'cards'

const VIEW_MODES: ViewMode[] = ['table', 'cards']

export function useViewMode(listKey: string, fallback: ViewMode = 'table') {
  const stored = useStorage<string>(`paprika:view-mode:${listKey}`, fallback)

  return computed<ViewMode>({
    get: () =>
      VIEW_MODES.includes(stored.value as ViewMode) ? (stored.value as ViewMode) : fallback,
    set: (mode) => {
      stored.value = mode
    },
  })
}
