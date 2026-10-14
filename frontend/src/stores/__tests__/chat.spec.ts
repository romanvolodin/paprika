import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChatStore } from '@/stores/chat'
import * as chatApi from '@/api/chat'
import type { MessageOut } from '@/types/api'

vi.mock('@/api/chat')

function buildMessage(id: number, overrides: Partial<MessageOut> = {}): MessageOut {
  return {
    id,
    shot_id: 10,
    type: 'user',
    text: `m${id}`,
    event: null,
    payload: {},
    reply_to: null,
    versions: [],
    attachments: [],
    reactions: [],
    edited_at: null,
    created_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

type ChatList = Awaited<ReturnType<typeof chatApi.listMessages>>

function chatList(ids: number[], hasOlder = false, shotId = 10): ChatList {
  return {
    items: ids.map((id) => buildMessage(id, { shot_id: shotId })),
    has_older: hasOlder,
    has_newer: false,
  }
}

describe('useChatStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('open loads the latest window of the shot chat', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValue(chatList([1, 2, 3], true))

    const store = useChatStore()
    await store.open(10)

    expect(chatApi.listMessages).toHaveBeenCalledWith(10, { limit: 50 })
    expect(store.items.map((m) => m.id)).toEqual([1, 2, 3])
    expect(store.hasOlder).toBe(true)
    expect(store.isLoading).toBe(false)
  })

  it('opening another shot clears the previous chat right away', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValue(chatList([1, 2]))
    const store = useChatStore()
    await store.open(10)

    let resolveSecond!: (value: ChatList) => void
    vi.mocked(chatApi.listMessages).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSecond = resolve
      }),
    )
    const pending = store.open(11)

    expect(store.items).toEqual([])

    resolveSecond(chatList([7], false, 11))
    await pending
    expect(store.items.map((m) => m.shot_id)).toEqual([11])
  })

  it('a slow response for an earlier shot does not overwrite the current one', async () => {
    let resolveFirst!: (value: ChatList) => void
    vi.mocked(chatApi.listMessages).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      }),
    )
    const store = useChatStore()
    const first = store.open(10)

    vi.mocked(chatApi.listMessages).mockResolvedValue(chatList([7], false, 11))
    await store.open(11)

    resolveFirst(chatList([1, 2], false, 10))
    await first

    expect(store.items.map((m) => m.shot_id)).toEqual([11])
    expect(store.isLoading).toBe(false)
  })

  describe('refresh', () => {
    it('adds new messages and applies edits and deletions inside the window', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValueOnce(chatList([1, 2, 3]))
      const store = useChatStore()
      await store.open(10)
      vi.mocked(chatApi.listMessages).mockResolvedValueOnce({
        items: [buildMessage(1), buildMessage(3, { text: 'edited' }), buildMessage(4)],
        has_older: false,
        has_newer: false,
      })

      await store.refresh()

      expect(store.items.map((m) => m.id)).toEqual([1, 3, 4])
      expect(store.items[1]?.text).toBe('edited')
    })

    it('keeps older history that was loaded earlier', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValueOnce(chatList([3, 4], true))
      const store = useChatStore()
      await store.open(10)
      vi.mocked(chatApi.listMessages).mockResolvedValueOnce(chatList([1, 2], false))
      await store.loadOlder()
      vi.mocked(chatApi.listMessages).mockResolvedValueOnce(chatList([3, 4, 5], true))

      await store.refresh()

      expect(store.items.map((m) => m.id)).toEqual([1, 2, 3, 4, 5])
      expect(store.hasOlder).toBe(false)
    })

    it('does nothing before a chat is open', async () => {
      const store = useChatStore()

      await store.refresh()

      expect(chatApi.listMessages).not.toHaveBeenCalled()
    })

    it('drops a response that arrives after another shot was opened', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValueOnce(chatList([1]))
      const store = useChatStore()
      await store.open(10)

      let resolveRefresh!: (value: ChatList) => void
      vi.mocked(chatApi.listMessages).mockReturnValueOnce(
        new Promise((resolve) => {
          resolveRefresh = resolve
        }),
      )
      const refreshing = store.refresh()
      vi.mocked(chatApi.listMessages).mockResolvedValueOnce(chatList([9], false, 11))
      await store.open(11)

      resolveRefresh(chatList([1, 2], false, 10))
      await refreshing

      expect(store.items.map((m) => m.shot_id)).toEqual([11])
    })
  })

  describe('loadOlder', () => {
    it('asks for the messages before the oldest one held and prepends them', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValueOnce(chatList([51, 52], true))
      const store = useChatStore()
      await store.open(10)
      vi.mocked(chatApi.listMessages).mockResolvedValueOnce(chatList([49, 50], false))

      await store.loadOlder()

      expect(chatApi.listMessages).toHaveBeenLastCalledWith(10, { limit: 50, before: 51 })
      expect(store.items.map((m) => m.id)).toEqual([49, 50, 51, 52])
      expect(store.hasOlder).toBe(false)
      expect(store.isLoadingOlder).toBe(false)
    })

    it('does not start a second load while one is running', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValueOnce(chatList([51], true))
      const store = useChatStore()
      await store.open(10)
      let resolveOlder!: (value: ChatList) => void
      vi.mocked(chatApi.listMessages).mockReturnValueOnce(
        new Promise((resolve) => {
          resolveOlder = resolve
        }),
      )
      const first = store.loadOlder()

      await store.loadOlder()
      resolveOlder(chatList([50], false))
      await first

      expect(chatApi.listMessages).toHaveBeenCalledTimes(2)
    })
  })

  it('send adds the created message to the end', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValue(chatList([1]))
    vi.mocked(chatApi.sendMessage).mockResolvedValue(buildMessage(2, { text: 'Hi' }))
    const store = useChatStore()
    await store.open(10)

    await store.send('Hi')

    expect(chatApi.sendMessage).toHaveBeenCalledWith(10, { text: 'Hi' })
    expect(store.items.map((m) => m.id)).toEqual([1, 2])
  })

  it('a failed send adds nothing', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValue(chatList([1]))
    vi.mocked(chatApi.sendMessage).mockRejectedValue(new Error('too long'))
    const store = useChatStore()
    await store.open(10)

    await expect(store.send('Hi')).rejects.toThrow('too long')
    expect(store.items.map((m) => m.id)).toEqual([1])
  })

  it('a message the poll already delivered is not added twice by send', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValue(chatList([1, 2]))
    vi.mocked(chatApi.sendMessage).mockResolvedValue(buildMessage(2, { text: 'Hi' }))
    const store = useChatStore()
    await store.open(10)

    await store.send('Hi')

    expect(store.items.map((m) => m.id)).toEqual([1, 2])
    expect(store.items[1]?.text).toBe('Hi')
  })

  it('edit replaces the message with the server response', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValue(chatList([1, 2]))
    vi.mocked(chatApi.editMessage).mockResolvedValue(
      buildMessage(2, { text: 'fixed', edited_at: '2026-01-02T00:00:00Z' }),
    )
    const store = useChatStore()
    await store.open(10)

    await store.edit(2, 'fixed')

    expect(chatApi.editMessage).toHaveBeenCalledWith(2, { text: 'fixed' })
    expect(store.items[1]?.text).toBe('fixed')
    expect(store.items[1]?.edited_at).not.toBeNull()
  })

  it('remove deletes the message and drops it from the list', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValue(chatList([1, 2]))
    vi.mocked(chatApi.deleteMessage).mockResolvedValue(undefined as never)
    const store = useChatStore()
    await store.open(10)

    await store.remove(1)

    expect(chatApi.deleteMessage).toHaveBeenCalledWith(1)
    expect(store.items.map((m) => m.id)).toEqual([2])
  })

  it('a failed remove keeps the message', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValue(chatList([1, 2]))
    vi.mocked(chatApi.deleteMessage).mockRejectedValue(new Error('forbidden'))
    const store = useChatStore()
    await store.open(10)

    await expect(store.remove(1)).rejects.toThrow('forbidden')
    expect(store.items.map((m) => m.id)).toEqual([1, 2])
  })
})
