import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useVersionsStore } from '@/stores/versions'
import * as versionsApi from '@/api/versions'
import type { VersionOut } from '@/types/api'

vi.mock('@/api/versions')

function buildVersion(overrides: Partial<VersionOut> = {}): VersionOut {
  return {
    id: 1,
    project_id: 1,
    shot_id: 10,
    name: 'PRJ_0010_v01',
    type: 'video',
    source: 'http://localhost/media/a.mp4',
    converted: null,
    thumb: null,
    width: 1920,
    height: 1080,
    duration: 240,
    fps: 24,
    codec: 'h264',
    file_size: 1024,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function mockList(items: VersionOut[], total = items.length) {
  vi.mocked(versionsApi.listVersions).mockResolvedValue({
    items,
    total,
    page: 1,
    page_size: 20,
  })
}

type ListResult = Awaited<ReturnType<typeof versionsApi.listVersions>>

describe('useVersionsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetch loads the first page of the shot versions', async () => {
    mockList([buildVersion()], 1)

    const store = useVersionsStore()
    await store.fetch(10)

    expect(versionsApi.listVersions).toHaveBeenCalledWith(10, { page: 1, page_size: 20 })
    expect(store.items).toHaveLength(1)
    expect(store.total).toBe(1)
    expect(store.isLoading).toBe(false)
  })

  it('setPage fetches that page', async () => {
    mockList([buildVersion()], 45)

    const store = useVersionsStore()
    await store.fetch(10)
    await store.setPage(10, 3)

    expect(versionsApi.listVersions).toHaveBeenLastCalledWith(10, { page: 3, page_size: 20 })
    expect(store.page).toBe(3)
  })

  it('fetching another shot clears the previous shot versions and page right away', async () => {
    mockList([buildVersion({ shot_id: 10 })], 45)
    const store = useVersionsStore()
    await store.fetch(10)
    await store.setPage(10, 2)

    let resolveSecond!: (value: ListResult) => void
    vi.mocked(versionsApi.listVersions).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSecond = resolve
      }),
    )
    const pending = store.fetch(11)

    expect(store.items).toEqual([])
    expect(store.page).toBe(1)

    resolveSecond({
      items: [buildVersion({ id: 2, shot_id: 11 })],
      total: 1,
      page: 1,
      page_size: 20,
    })
    await pending
    expect(store.items.map((version) => version.shot_id)).toEqual([11])
  })

  it('a slow response for an earlier shot does not overwrite the current one', async () => {
    let resolveFirst!: (value: ListResult) => void
    vi.mocked(versionsApi.listVersions).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      }),
    )
    const store = useVersionsStore()
    const first = store.fetch(10)

    mockList([buildVersion({ id: 2, shot_id: 11 })])
    await store.fetch(11)

    resolveFirst({ items: [buildVersion({ shot_id: 10 })], total: 1, page: 1, page_size: 20 })
    await first

    expect(store.items.map((version) => version.shot_id)).toEqual([11])
    expect(store.isLoading).toBe(false)
  })

  describe('upload', () => {
    const file = new File(['x'], 'PRJ_0010_v02.mp4', { type: 'video/mp4' })

    it('reports progress, switches to processing after the last byte, then refetches page one', async () => {
      mockList([buildVersion()])
      const seen: Array<[string, number]> = []
      const store = useVersionsStore()
      await store.fetch(10)
      await store.setPage(10, 2)
      vi.mocked(versionsApi.uploadVersion).mockImplementation(async (_id, _file, onProgress) => {
        onProgress?.(50, 100)
        seen.push([store.uploadState, store.uploadProgress])
        onProgress?.(100, 100)
        seen.push([store.uploadState, store.uploadProgress])
        return buildVersion({ id: 2 })
      })

      const created = await store.upload(10, file)

      expect(created.id).toBe(2)
      expect(seen).toEqual([
        ['uploading', 50],
        ['processing', 100],
      ])
      expect(versionsApi.uploadVersion).toHaveBeenCalledWith(10, file, expect.any(Function))
      expect(store.uploadState).toBe('idle')
      expect(store.uploadProgress).toBe(0)
      expect(store.page).toBe(1)
      expect(versionsApi.listVersions).toHaveBeenLastCalledWith(10, { page: 1, page_size: 20 })
    })

    it('goes back to idle and does not refetch when the upload fails', async () => {
      vi.mocked(versionsApi.uploadVersion).mockRejectedValue(new Error('duplicate'))
      const store = useVersionsStore()

      await expect(store.upload(10, file)).rejects.toThrow('duplicate')

      expect(store.uploadState).toBe('idle')
      expect(store.uploadProgress).toBe(0)
      expect(versionsApi.listVersions).not.toHaveBeenCalled()
    })
  })

  describe('remove', () => {
    it('deletes the version and refetches', async () => {
      mockList([])
      vi.mocked(versionsApi.deleteVersion).mockResolvedValue(undefined as never)

      const store = useVersionsStore()
      await store.remove(10, 1)

      expect(versionsApi.deleteVersion).toHaveBeenCalledWith(1)
      expect(versionsApi.listVersions).toHaveBeenCalledTimes(1)
    })

    it('steps back a page when deleting emptied the last page', async () => {
      mockList([buildVersion()], 21)
      const store = useVersionsStore()
      await store.fetch(10)
      await store.setPage(10, 2)
      vi.mocked(versionsApi.deleteVersion).mockResolvedValue(undefined as never)
      vi.mocked(versionsApi.listVersions)
        .mockResolvedValueOnce({ items: [], total: 20, page: 2, page_size: 20 })
        .mockResolvedValueOnce({ items: [buildVersion()], total: 20, page: 1, page_size: 20 })

      await store.remove(10, 1)

      expect(store.page).toBe(1)
      expect(store.items).toHaveLength(1)
    })
  })
})
