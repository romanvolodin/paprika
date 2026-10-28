import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
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

function mockCompanies(items: CompanyOut[]) {
  vi.mocked(companiesApi.listCompanies).mockResolvedValue({
    items,
    total: items.length,
    page: 1,
    page_size: 100,
  })
}

describe('useCurrentCompanyStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('has no selection and is not initialized before initialize() runs', () => {
    const store = useCurrentCompanyStore()
    expect(store.isInitialized).toBe(false)
    expect(store.currentCompany).toBeNull()
    expect(store.needsSelection).toBe(false)
  })

  it('auto-selects the only company when there is exactly one', async () => {
    mockCompanies([buildCompany({ id: 5 })])

    const store = useCurrentCompanyStore()
    await store.initialize()

    expect(store.currentCompanyId).toBe(5)
    expect(store.currentCompany?.id).toBe(5)
    expect(store.needsSelection).toBe(false)
    expect(localStorage.getItem('paprika:current-company-id')).toBe('5')
  })

  it('does not gate on selection when the user has no companies', async () => {
    mockCompanies([])

    const store = useCurrentCompanyStore()
    await store.initialize()

    expect(store.currentCompany).toBeNull()
    expect(store.needsSelection).toBe(false)
  })

  it('keeps a previously stored selection across a fresh tab/reload', async () => {
    localStorage.setItem('paprika:current-company-id', '7')
    mockCompanies([buildCompany({ id: 7, name: 'Second Studio' }), buildCompany({ id: 9 })])

    const store = useCurrentCompanyStore()
    await store.initialize()

    expect(store.currentCompanyId).toBe(7)
    expect(store.currentCompany?.name).toBe('Second Studio')
    expect(store.needsSelection).toBe(false)
  })

  it('requires an explicit pick when there are multiple companies and no valid stored id', async () => {
    mockCompanies([buildCompany({ id: 1 }), buildCompany({ id: 2 })])

    const store = useCurrentCompanyStore()
    await store.initialize()

    expect(store.currentCompany).toBeNull()
    expect(store.needsSelection).toBe(true)
  })

  it('clears a stale stored id that no longer matches any company (e.g. removed membership)', async () => {
    localStorage.setItem('paprika:current-company-id', '999')
    mockCompanies([buildCompany({ id: 1 }), buildCompany({ id: 2 })])

    const store = useCurrentCompanyStore()
    await store.initialize()

    expect(store.currentCompanyId).toBeNull()
    expect(store.needsSelection).toBe(true)
  })

  it('selectCompany persists the pick and resolves needsSelection', async () => {
    mockCompanies([buildCompany({ id: 1 }), buildCompany({ id: 2, name: 'Second' })])

    const store = useCurrentCompanyStore()
    await store.initialize()
    expect(store.needsSelection).toBe(true)

    store.selectCompany(2)

    expect(store.currentCompanyId).toBe(2)
    expect(store.currentCompany?.name).toBe('Second')
    expect(store.needsSelection).toBe(false)
  })

  it('reset clears the selection, companies and initialized flag', async () => {
    mockCompanies([buildCompany({ id: 1 })])
    const store = useCurrentCompanyStore()
    await store.initialize()

    store.reset()
    // The underlying useStorage ref writes to localStorage via a
    // 'pre'-flush watcher, which runs on the next microtask rather than
    // synchronously - give it a tick before checking the raw storage.
    await nextTick()

    expect(store.currentCompanyId).toBeNull()
    expect(store.companies).toHaveLength(0)
    expect(store.isInitialized).toBe(false)
    expect(localStorage.getItem('paprika:current-company-id')).toBeNull()
  })

  it('refreshCompanies picks up a newly created company without touching an existing selection', async () => {
    mockCompanies([buildCompany({ id: 1 })])
    const store = useCurrentCompanyStore()
    await store.initialize()
    expect(store.currentCompanyId).toBe(1)

    mockCompanies([buildCompany({ id: 1 }), buildCompany({ id: 2, name: 'New Studio' })])
    await store.refreshCompanies()

    expect(store.companies).toHaveLength(2)
    expect(store.currentCompanyId).toBe(1)
    expect(store.needsSelection).toBe(false)
  })

  it('refreshCompanies auto-selects a first company created from zero', async () => {
    mockCompanies([])
    const store = useCurrentCompanyStore()
    await store.initialize()
    expect(store.currentCompanyId).toBeNull()

    mockCompanies([buildCompany({ id: 3, name: 'First Studio' })])
    await store.refreshCompanies()

    expect(store.currentCompanyId).toBe(3)
    expect(store.currentCompany?.name).toBe('First Studio')
  })
})
