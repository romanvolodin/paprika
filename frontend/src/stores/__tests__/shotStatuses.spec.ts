import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useShotStatusesStore } from '@/stores/shotStatuses'
import * as shotsApi from '@/api/shots'
import type { ShotStatusOut } from '@/types/api'

vi.mock('@/api/shots')

function buildStatus(overrides: Partial<ShotStatusOut> = {}): ShotStatusOut {
  return {
    id: 1,
    company_id: 7,
    name: 'In progress',
    color: '#3366ff',
    order: 1,
    is_default: false,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function mockList(items: ShotStatusOut[]) {
  vi.mocked(shotsApi.listShotStatuses).mockResolvedValue({ items })
}

describe('useShotStatusesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetch loads the company statuses', async () => {
    mockList([buildStatus()])

    const store = useShotStatusesStore()
    await store.fetch(7)

    expect(shotsApi.listShotStatuses).toHaveBeenCalledWith(7)
    expect(store.items).toHaveLength(1)
    expect(store.isLoading).toBe(false)
  })

  it('create posts the input and refetches', async () => {
    mockList([buildStatus(), buildStatus({ id: 2, name: 'Review' })])
    vi.mocked(shotsApi.createShotStatus).mockResolvedValue(buildStatus({ id: 2 }))

    const store = useShotStatusesStore()
    const input = { name: 'Review', color: '#aabbcc', order: null, is_default: false }
    await store.create(7, input)

    expect(shotsApi.createShotStatus).toHaveBeenCalledWith(7, input)
    expect(store.items).toHaveLength(2)
  })

  it('update refetches the whole list so a moved default is picked up', async () => {
    mockList([
      buildStatus({ id: 1, is_default: false }),
      buildStatus({ id: 2, name: 'New', is_default: true }),
    ])
    vi.mocked(shotsApi.updateShotStatus).mockResolvedValue(buildStatus({ id: 2 }))

    const store = useShotStatusesStore()
    const input = { name: 'New', color: '#3366ff', order: 1, is_default: true }
    await store.update(7, 2, input)

    expect(shotsApi.updateShotStatus).toHaveBeenCalledWith(2, input)
    expect(store.items.map((status) => status.is_default)).toEqual([false, true])
  })

  it('remove deletes the status and refetches', async () => {
    mockList([])
    vi.mocked(shotsApi.deleteShotStatus).mockResolvedValue(undefined as never)

    const store = useShotStatusesStore()
    await store.remove(7, 1)

    expect(shotsApi.deleteShotStatus).toHaveBeenCalledWith(1)
    expect(store.items).toEqual([])
  })

  it('a failed delete does not refetch', async () => {
    vi.mocked(shotsApi.deleteShotStatus).mockRejectedValue(new Error('in use'))

    const store = useShotStatusesStore()

    await expect(store.remove(7, 1)).rejects.toThrow('in use')
    expect(shotsApi.listShotStatuses).not.toHaveBeenCalled()
  })

  it('fetching another company clears the previous company statuses right away', async () => {
    mockList([buildStatus({ id: 1, company_id: 7 })])
    const store = useShotStatusesStore()
    await store.fetch(7)

    let resolveSecond!: (value: Awaited<ReturnType<typeof shotsApi.listShotStatuses>>) => void
    vi.mocked(shotsApi.listShotStatuses).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveSecond = resolve
      }),
    )
    const pending = store.fetch(8)

    expect(store.items).toEqual([])

    resolveSecond({ items: [buildStatus({ id: 2, company_id: 8 })] })
    await pending
    expect(store.items.map((status) => status.company_id)).toEqual([8])
  })

  it('a slow response for an earlier company does not overwrite the current one', async () => {
    let resolveFirst!: (value: Awaited<ReturnType<typeof shotsApi.listShotStatuses>>) => void
    vi.mocked(shotsApi.listShotStatuses).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFirst = resolve
      }),
    )
    const store = useShotStatusesStore()
    const first = store.fetch(7)

    mockList([buildStatus({ id: 2, company_id: 8 })])
    await store.fetch(8)

    resolveFirst({ items: [buildStatus({ id: 1, company_id: 7 })] })
    await first

    expect(store.items.map((status) => status.company_id)).toEqual([8])
    expect(store.isLoading).toBe(false)
  })
})
