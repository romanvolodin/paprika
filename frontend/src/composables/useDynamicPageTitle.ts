import { toValue, watch, type MaybeRefOrGetter } from 'vue'
import { buildPageTitle } from '@/utils/pageTitle'

export function useDynamicPageTitle(title: MaybeRefOrGetter<string | null | undefined>) {
  watch(
    () => toValue(title),
    (value) => {
      if (value) document.title = buildPageTitle([value])
    },
    { immediate: true },
  )
}
