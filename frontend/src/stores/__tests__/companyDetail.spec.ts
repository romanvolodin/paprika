import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useCompanyDetailStore } from '@/stores/companyDetail'
import * as companiesApi from '@/api/companies'
import * as rolesApi from '@/api/roles'
import type { CompanyMemberOut, CompanyOut, RoleOut, RoleRefOut } from '@/types/api'

vi.mock('@/api/companies')
vi.mock('@/api/roles')

function buildRole(overrides: Partial<RoleRefOut> = {}): RoleRefOut {
  return { id: 1, name: 'Админ', color: '#00A64F', ...overrides }
}

function buildRoleOut(overrides: Partial<RoleOut> = {}): RoleOut {
  return {
    id: 1,
    company_id: 1,
    name: 'Админ',
    color: '#00A64F',
    permissions: [],
    sees_all_projects: true,
    company_members_count: 0,
    project_members_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

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

function buildMember(overrides: Partial<CompanyMemberOut> = {}): CompanyMemberOut {
  return {
    id: 1,
    user_id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    role: buildRole(),
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('useCompanyDetailStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(rolesApi.listCompanyRoles).mockResolvedValue({ items: [] })
  })

  describe('fetch', () => {
    it('loads the company, its members and its roles together', async () => {
      vi.mocked(rolesApi.listCompanyRoles).mockResolvedValue({ items: [buildRoleOut()] })
      vi.mocked(companiesApi.getCompany).mockResolvedValue(buildCompany())
      vi.mocked(companiesApi.listCompanyMembers).mockResolvedValue({
        items: [buildMember()],
      })

      const store = useCompanyDetailStore()
      await store.fetch(1)

      expect(companiesApi.getCompany).toHaveBeenCalledWith(1)
      expect(companiesApi.listCompanyMembers).toHaveBeenCalledWith(1)
      expect(store.company).toEqual(buildCompany())
      expect(store.members).toHaveLength(1)
      expect(rolesApi.listCompanyRoles).toHaveBeenCalledWith(1)
      expect(store.roles).toHaveLength(1)
      expect(store.isLoading).toBe(false)
    })

    it('sets isLoading while the fetch is in flight', async () => {
      let resolveCompany!: (value: CompanyOut) => void
      vi.mocked(companiesApi.getCompany).mockReturnValue(
        new Promise((resolve) => {
          resolveCompany = resolve
        }),
      )
      vi.mocked(companiesApi.listCompanyMembers).mockResolvedValue({ items: [] })

      const store = useCompanyDetailStore()
      const pending = store.fetch(1)
      expect(store.isLoading).toBe(true)

      resolveCompany(buildCompany())
      await pending

      expect(store.isLoading).toBe(false)
    })
  })

  describe('updateCompany', () => {
    it('replaces the local company with the server response', async () => {
      vi.mocked(companiesApi.updateCompany).mockResolvedValue(buildCompany({ name: 'Renamed' }))

      const store = useCompanyDetailStore()
      await store.updateCompany(1, { name: 'Renamed' })

      expect(companiesApi.updateCompany).toHaveBeenCalledWith(1, { name: 'Renamed' })
      expect(store.company?.name).toBe('Renamed')
    })
  })

  describe('addMember', () => {
    it('adds the member then refetches the members list', async () => {
      vi.mocked(companiesApi.addCompanyMember).mockResolvedValue(buildMember())
      vi.mocked(companiesApi.listCompanyMembers).mockResolvedValue({
        items: [buildMember()],
      })

      const store = useCompanyDetailStore()
      await store.addMember(1, { user_id: 1, role_id: 4 })

      expect(companiesApi.addCompanyMember).toHaveBeenCalledWith(1, {
        user_id: 1,
        role_id: 4,
      })
      expect(companiesApi.listCompanyMembers).toHaveBeenCalledWith(1)
      expect(store.members).toHaveLength(1)
    })
  })

  describe('updateMemberRole', () => {
    it('updates the role then refetches the members list', async () => {
      vi.mocked(companiesApi.updateCompanyMember).mockResolvedValue(
        buildMember({ role: buildRole({ id: 3, name: 'Координатор' }) }),
      )
      vi.mocked(companiesApi.listCompanyMembers).mockResolvedValue({
        items: [buildMember({ role: buildRole({ id: 3, name: 'Координатор' }) })],
      })

      const store = useCompanyDetailStore()
      await store.updateMemberRole(1, 1, 3)

      expect(companiesApi.updateCompanyMember).toHaveBeenCalledWith(1, 1, {
        role_id: 3,
      })
      expect(store.members[0]?.role.name).toBe('Координатор')
    })
  })

  describe('removeMember', () => {
    it('removes the member then refetches the members list', async () => {
      vi.mocked(companiesApi.removeCompanyMember).mockResolvedValue(
        undefined as unknown as Awaited<ReturnType<typeof companiesApi.removeCompanyMember>>,
      )
      vi.mocked(companiesApi.listCompanyMembers).mockResolvedValue({ items: [] })

      const store = useCompanyDetailStore()
      await store.removeMember(1, 1)

      expect(companiesApi.removeCompanyMember).toHaveBeenCalledWith(1, 1)
      expect(store.members).toHaveLength(0)
    })
  })
})
