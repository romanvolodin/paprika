import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as chatApi from '@/api/chat'
import { mergeLatestWindow } from '@/utils/chat'
import type { MessageOut } from '@/types/api'

const PAGE_SIZE = 50

export const useChatStore = defineStore('chat', () => {
  const items = ref<MessageOut[]>([])
  const hasOlder = ref(false)
  const isLoading = ref(false)
  const isLoadingOlder = ref(false)

  // The store is shared by every shot page, so it remembers which shot
  // it was opened for and ignores responses for one the user left.
  let shotId: number | null = null
  let requestToken = 0

  async function open(nextShotId: number) {
    const token = ++requestToken
    if (shotId !== nextShotId) {
      items.value = []
      hasOlder.value = false
      shotId = nextShotId
    }
    isLoading.value = true
    try {
      const result = await chatApi.listMessages(nextShotId, { limit: PAGE_SIZE })
      if (token !== requestToken) return
      items.value = result.items
      hasOlder.value = result.has_older
    } finally {
      if (token === requestToken) isLoading.value = false
    }
  }

  /** Picks up new, edited and deleted messages without a loading state. */
  async function refresh() {
    if (shotId === null) return
    const token = requestToken
    const currentShotId = shotId
    const result = await chatApi.listMessages(currentShotId, { limit: PAGE_SIZE })
    // `open` or another shot's refresh happened meanwhile - drop this one.
    if (token !== requestToken || currentShotId !== shotId) return
    const merged = mergeLatestWindow(items.value, result.items, result.has_older)
    items.value = merged.items
    if (merged.hasOlder !== null) hasOlder.value = merged.hasOlder
  }

  async function loadOlder() {
    const oldest = items.value[0]
    if (shotId === null || !oldest || isLoadingOlder.value) return
    const token = requestToken
    isLoadingOlder.value = true
    try {
      const result = await chatApi.listMessages(shotId, { limit: PAGE_SIZE, before: oldest.id })
      if (token !== requestToken) return
      items.value = [...result.items, ...items.value]
      hasOlder.value = result.has_older
    } finally {
      isLoadingOlder.value = false
    }
  }

  function upsert(message: MessageOut) {
    const exists = items.value.some((item) => item.id === message.id)
    items.value = exists
      ? items.value.map((item) => (item.id === message.id ? message : item))
      : [...items.value, message].sort((a, b) => a.id - b.id)
  }

  async function send(text: string, replyToId: number | null = null) {
    if (shotId === null) return
    upsert(
      await chatApi.sendMessage(shotId, {
        text,
        ...(replyToId === null ? {} : { reply_to_id: replyToId }),
      }),
    )
  }

  async function edit(messageId: number, text: string) {
    upsert(await chatApi.editMessage(messageId, { text }))
  }

  /** Puts (`on`) or removes the current user's emoji on a message. */
  async function react(messageId: number, emoji: string, on: boolean) {
    const { reactions } = on
      ? await chatApi.putReaction(messageId, emoji)
      : await chatApi.removeReaction(messageId, emoji)
    items.value = items.value.map((item) => (item.id === messageId ? { ...item, reactions } : item))
  }

  async function remove(messageId: number) {
    await chatApi.deleteMessage(messageId)
    items.value = items.value.filter((item) => item.id !== messageId)
  }

  return {
    items,
    hasOlder,
    isLoading,
    isLoadingOlder,
    open,
    refresh,
    loadOlder,
    send,
    edit,
    react,
    remove,
  }
})
