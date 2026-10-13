import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useShotGroupsStore } from '@/stores/shotGroups'
import * as shotsApi from '@/api/shots'
import type { ShotGroupOut } from '@/types/api'

vi.mock('@/api/shots')

function buildGroup(overrides: Partial<ShotGroupOut> = {}): ShotGroupOut {
  return {
    id: 1,
    project_id: 5,
    name: 'Int. Office',
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function mockList(items: ShotGroupOut[]) {
  vi.mocked(shotsApi.listShotGroups).mockResolvedValue({
    items,
    total: items.length,
    page: 1,
    page_size: 100,
  })
}

describe('useShotGroupsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetch loads the project groups', async () => {
    mockList([buildGroup()])

    const store = useShotGroupsStore()
    await store.fetch(5)

    expect(shotsApi.listShotGroups).toHaveBeenCalledWith(5, { page_size: 100 })
    expect(store.items).toHaveLength(1)
    expect(store.isLoading).toBe(false)
  })

  it('create posts the name and refetches', async () => {
    mockList([buildGroup(), buildGroup({ id: 2, name: 'Ext. Street' })])
    vi.mocked(shotsApi.createShotGroup).mockResolvedValue(buildGroup({ id: 2 }))

    const store = useShotGroupsStore()
    await store.create(5, 'Ext. Street')

    expect(shotsApi.createShotGroup).toHaveBeenCalledWith(5, { name: 'Ext. Street' })
    expect(store.items).toHaveLength(2)
  })

  it('rename patches the group and refetches', async () => {
    mockList([buildGroup({ name: 'Renamed' })])
    vi.mocked(shotsApi.renameShotGroup).mockResolvedValue(buildGroup({ name: 'Renamed' }))

    const store = useShotGroupsStore()
    await store.rename(5, 1, 'Renamed')

    expect(shotsApi.renameShotGroup).toHaveBeenCalledWith(1, { name: 'Renamed' })
    expect(store.items[0]?.name).toBe('Renamed')
  })

  it('remove deletes the group and refetches', async () => {
    mockList([])
    vi.mocked(shotsApi.deleteShotGroup).mockResolvedValue(undefined as never)

    const store = useShotGroupsStore()
    await store.remove(5, 1)

    expect(shotsApi.deleteShotGroup).toHaveBeenCalledWith(1)
    expect(store.items).toEqual([])
  })

  it('a failed create does not refetch', async () => {
    vi.mocked(shotsApi.createShotGroup).mockRejectedValue(new Error('duplicate'))

    const store = useShotGroupsStore()

    await expect(store.create(5, 'Int. Office')).rejects.toThrow('duplicate')
    expect(shotsApi.listShotGroups).not.toHaveBeenCalled()
  })

  it('fetching another project clears the previous project groups right away', async () => {
    mockList([buildGroup({ id: 1, project_id: 5 })])
    const store = useShotGroupsStore()
    await store.fetch(5)

    let resolveSecond!: (value: Awaited<ReturnType<typeof shotsApi.listShotGroups>>) => void
    vi.mocked(shotsApi.listShotGroups).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSecond = resolve
      }),
    )
    const pending = store.fetch(6)

    expect(store.items).toEqual([])

    resolveSecond({
      items: [buildGroup({ id: 2, project_id: 6 })],
      total: 1,
      page: 1,
      page_size: 100,
    })
    await pending
    expect(store.items.map((group) => group.project_id)).toEqual([6])
  })

  it('a slow response for an earlier project does not overwrite the current one', async () => {
    let resolveFirst!: (value: Awaited<ReturnType<typeof shotsApi.listShotGroups>>) => void
    vi.mocked(shotsApi.listShotGroups).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      }),
    )
    const store = useShotGroupsStore()
    const first = store.fetch(5)

    mockList([buildGroup({ id: 2, project_id: 6 })])
    await store.fetch(6)

    resolveFirst({
      items: [buildGroup({ id: 1, project_id: 5 })],
      total: 1,
      page: 1,
      page_size: 100,
    })
    await first

    expect(store.items.map((group) => group.project_id)).toEqual([6])
    expect(store.isLoading).toBe(false)
  })
})
