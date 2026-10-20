import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useShotReviewStore } from '@/stores/shotReview'
import * as versionsApi from '@/api/versions'
import type { VersionOut } from '@/types/api'

vi.mock('@/api/versions')

function buildVersion(id: number, name: string): VersionOut {
  return {
    id,
    project_id: 1,
    shot_id: 5,
    name,
    type: 'video',
    source: `/media/${name}.mp4`,
    converted: null,
    thumb: null,
    width: 1920,
    height: 1080,
    duration: 96,
    fps: 24,
    codec: 'h264',
    file_size: 1000,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

// Newest first, as the API returns them.
const v3 = buildVersion(3, 'PRJ_0010_v03')
const v2 = buildVersion(2, 'PRJ_0010_v02')
const v1 = buildVersion(1, 'PRJ_0010_v01')

function listOf(items: VersionOut[], total = items.length) {
  return { items, total, page: 1, page_size: 100 }
}

describe('shotReview store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('plays the newest version when none is asked for', async () => {
    vi.mocked(versionsApi.listVersions).mockResolvedValue(listOf([v3, v2, v1]))
    const store = useShotReviewStore()

    await store.load(5, null)

    expect(store.state).toBe('ready')
    expect(store.current?.name).toBe('PRJ_0010_v03')
    expect(versionsApi.listVersions).toHaveBeenCalledWith(5, { page_size: 100 })
  })

  it('plays the version asked for by name', async () => {
    vi.mocked(versionsApi.listVersions).mockResolvedValue(listOf([v3, v2, v1]))
    const store = useShotReviewStore()

    await store.load(5, 'PRJ_0010_v02')

    expect(store.state).toBe('ready')
    expect(store.current?.id).toBe(2)
  })

  it('switches to another version of the loaded shot without reloading', async () => {
    vi.mocked(versionsApi.listVersions).mockResolvedValue(listOf([v3, v2, v1]))
    const store = useShotReviewStore()
    await store.load(5, null)

    await store.select(5, 'PRJ_0010_v01')

    expect(store.current?.id).toBe(1)
    expect(versionsApi.listVersions).toHaveBeenCalledTimes(1)
  })

  it('falls back to the newest version when the name is dropped from the address', async () => {
    vi.mocked(versionsApi.listVersions).mockResolvedValue(listOf([v3, v2, v1]))
    const store = useShotReviewStore()
    await store.load(5, 'PRJ_0010_v01')

    await store.select(5, null)

    expect(store.current?.id).toBe(3)
  })

  it('says the version is not found when no such name exists', async () => {
    vi.mocked(versionsApi.listVersions).mockResolvedValue(listOf([v3, v2, v1]))
    const store = useShotReviewStore()

    await store.load(5, 'PRJ_0010_v99')

    expect(store.state).toBe('not-found')
    expect(store.current).toBeNull()
  })

  it('looks an older version up by name when more exist than were loaded', async () => {
    vi.mocked(versionsApi.listVersions)
      .mockResolvedValueOnce(listOf([v3, v2], 150))
      .mockResolvedValueOnce(listOf([v1], 1))
    const store = useShotReviewStore()

    await store.load(5, 'PRJ_0010_v01')

    expect(store.state).toBe('ready')
    expect(store.current?.id).toBe(1)
    expect(versionsApi.listVersions).toHaveBeenLastCalledWith(5, {
      search: 'PRJ_0010_v01',
      page_size: 100,
    })
  })

  it('does not look the name up again when every version was loaded', async () => {
    vi.mocked(versionsApi.listVersions).mockResolvedValue(listOf([v3, v2, v1]))
    const store = useShotReviewStore()

    await store.load(5, 'PRJ_0010_v99')

    expect(versionsApi.listVersions).toHaveBeenCalledTimes(1)
  })

  it('is empty for a shot without versions', async () => {
    vi.mocked(versionsApi.listVersions).mockResolvedValue(listOf([]))
    const store = useShotReviewStore()

    await store.load(5, null)

    expect(store.state).toBe('empty')
    expect(store.current).toBeNull()
  })

  it('reports an error when loading fails', async () => {
    vi.mocked(versionsApi.listVersions).mockRejectedValue(new Error('boom'))
    const store = useShotReviewStore()

    await store.load(5, null)

    expect(store.state).toBe('error')
  })

  it('ignores a response for a shot the reader already left', async () => {
    let resolveFirst: (value: ReturnType<typeof listOf>) => void = () => {}
    vi.mocked(versionsApi.listVersions)
      .mockImplementationOnce(() => new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce(listOf([v1]))
    const store = useShotReviewStore()

    const first = store.load(5, null)
    await store.load(6, null)
    resolveFirst(listOf([v3, v2]))
    await first

    expect(store.current?.id).toBe(1)
  })

  it('reloads the versions each time the tab is opened', async () => {
    vi.mocked(versionsApi.listVersions)
      .mockResolvedValueOnce(listOf([v2, v1]))
      .mockResolvedValueOnce(listOf([v3, v2, v1]))
    const store = useShotReviewStore()

    await store.load(5, null)
    await store.load(5, null)

    expect(store.current?.id).toBe(3)
  })
})
