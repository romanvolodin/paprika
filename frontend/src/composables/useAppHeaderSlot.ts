import { shallowRef } from 'vue'

export const appHeaderSlot = shallowRef<HTMLElement | null>(null)

export function setAppHeaderSlot(element: unknown) {
  appHeaderSlot.value = element instanceof HTMLElement ? element : null
}
