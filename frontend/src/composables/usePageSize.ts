import { computed } from 'vue'
import { useStorage } from '@vueuse/core'

export const PAGE_SIZE_OPTIONS = [20, 50, 100, 200, 500]

export const DEFAULT_PAGE_SIZE = 50

export function usePageSize(
  listKey: string,
  options: number[] = PAGE_SIZE_OPTIONS,
  fallback: number = DEFAULT_PAGE_SIZE,
) {
  const stored = useStorage<number>(`paprika:page-size:${listKey}`, fallback)

  return computed<number>({
    get: () => (options.includes(stored.value) ? stored.value : fallback),
    set: (size) => {
      stored.value = size
    },
  })
}
