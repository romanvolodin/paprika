import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCompaniesStore } from '@/stores/companies'
import * as companiesApi from '@/api/companies'
import type { CompanyOut } from '@/types/api'

vi.mock('@/api/companies')

function buildCompany(overrides: Partial<CompanyOut> = {}): CompanyOut {
  return {
    id: 1,
    name: 'Acme Studio',
    slug: 'acme-studio',
    my_permissions: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('useCompaniesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchCompanies loads a page and mirrors the server-confirmed pagination back', async () => {
    vi.mocked(companiesApi.listCompanies).mockResolvedValue({
      items: [buildCompany()],
      total: 1,
      page: 1,
      page_size: 20,
    })

    const store = useCompaniesStore()
    await store.fetchCompanies()

    expect(companiesApi.listCompanies).toHaveBeenCalledWith({
      page: 1,
      page_size: 20,
      search: undefined,
    })
    expect(store.items).toHaveLength(1)
    expect(store.total).toBe(1)
    expect(store.isLoading).toBe(false)
  })

  it('sets isLoading while a fetch is in flight', async () => {
    let resolveFetch!: (value: Awaited<ReturnType<typeof companiesApi.listCompanies>>) => void
    vi.mocked(companiesApi.listCompanies).mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve
      }),
    )

    const store = useCompaniesStore()
    const pending = store.fetchCompanies()
    expect(store.isLoading).toBe(true)

    resolveFetch({ items: [], total: 0, page: 1, page_size: 20 })
    await pending

    expect(store.isLoading).toBe(false)
  })

  it('setSearch resets to page 1 and refetches with the search term', async () => {
    vi.mocked(companiesApi.listCompanies).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    })

    const store = useCompaniesStore()
    store.page = 3

    await store.setSearch('acme')

    expect(store.search).toBe('acme')
    expect(companiesApi.listCompanies).toHaveBeenCalledWith({
      page: 1,
      page_size: 20,
      search: 'acme',
    })
  })

  it('setPage refetches with the requested page', async () => {
    vi.mocked(companiesApi.listCompanies).mockResolvedValue({
      items: [],
      total: 0,
      page: 2,
      page_size: 20,
    })

    const store = useCompaniesStore()
    await store.setPage(2)

    expect(companiesApi.listCompanies).toHaveBeenCalledWith({
      page: 2,
      page_size: 20,
      search: undefined,
    })
  })
})
