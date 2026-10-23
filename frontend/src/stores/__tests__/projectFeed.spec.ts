import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectFeedStore } from '@/stores/projectFeed'
import * as feedApi from '@/api/feed'
import type { FeedItemOut } from '@/types/api'

vi.mock('@/api/feed')

function buildItem(key: string): FeedItemOut {
  return {
    key,
    type: 'chat',
    created_at: '2026-10-21T10:00:00Z',
    created_by: null,
    shot: { id: 1, name: '0010' },
    text: 'Привет',
    attachments: [],
    versions: [],
    version: null,
    event: null,
    payload: {},
  }
}

describe('useProjectFeedStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(feedApi.listFeed).mockResolvedValue({
      items: [buildItem('chat-1')],
      next_before_date: '2026-10-16T10:00:00Z',
    })
  })

  it('open loads the newest slice with no filters', async () => {
    const store = useProjectFeedStore()

    await store.open(5)

    expect(feedApi.listFeed).toHaveBeenCalledWith(5, {
      mine: undefined,
      type: undefined,
      before_date: undefined,
    })
    expect(store.items.map((i) => i.key)).toEqual(['chat-1'])
    expect(store.hasMore).toBe(true)
    expect(store.state).toBe('ready')
  })

  it('loadMore asks for events before the cursor and appends them', async () => {
    const store = useProjectFeedStore()
    await store.open(5)
    vi.mocked(feedApi.listFeed).mockResolvedValue({
      items: [buildItem('chat-0')],
      next_before_date: null,
    })

    await store.loadMore()

    expect(feedApi.listFeed).toHaveBeenLastCalledWith(
      5,
      expect.objectContaining({ before_date: '2026-10-16T10:00:00Z' }),
    )
    expect(store.items.map((i) => i.key)).toEqual(['chat-1', 'chat-0'])
    expect(store.hasMore).toBe(false)
  })

  it('loadMore keeps the loaded events and flags a failure', async () => {
    const store = useProjectFeedStore()
    await store.open(5)
    vi.mocked(feedApi.listFeed).mockRejectedValue(new Error('boom'))

    await store.loadMore()

    expect(store.items).toHaveLength(1)
    expect(store.loadMoreFailed).toBe(true)
    expect(store.hasMore).toBe(true)
  })

  it('setScope("mine") reloads with mine=true', async () => {
    const store = useProjectFeedStore()
    await store.open(5)

    await store.setScope('mine')

    expect(feedApi.listFeed).toHaveBeenLastCalledWith(5, expect.objectContaining({ mine: true }))
    expect(store.isDefaultFilter).toBe(false)
  })

  it('setTypes sends the chosen types, and every type ticked sends no type', async () => {
    const store = useProjectFeedStore()
    await store.open(5)

    await store.setTypes(['task', 'chat'])
    expect(feedApi.listFeed).toHaveBeenLastCalledWith(
      5,
      expect.objectContaining({ type: 'chat,task' }),
    )

    await store.setTypes(['chat', 'version', 'task'])
    expect(store.types).toEqual(['chat', 'version', 'task'])
    expect(feedApi.listFeed).toHaveBeenLastCalledWith(
      5,
      expect.objectContaining({ type: undefined }),
    )
  })

  it('resetFilters goes back to the whole project and all types', async () => {
    const store = useProjectFeedStore()
    await store.open(5)
    await store.setScope('mine')
    await store.setTypes(['chat'])

    await store.resetFilters()

    expect(store.scope).toBe('project')
    expect(store.types).toEqual([])
    expect(store.isDefaultFilter).toBe(true)
  })

  it('goes to the error state when the first load fails', async () => {
    vi.mocked(feedApi.listFeed).mockRejectedValue(new Error('boom'))
    const store = useProjectFeedStore()

    await store.open(5)

    expect(store.state).toBe('error')
    expect(store.items).toEqual([])
  })
})
