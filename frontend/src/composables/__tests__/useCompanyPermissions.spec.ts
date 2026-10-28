import { beforeEach, describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { useCompanyPermissions } from '@/composables/useCompanyPermissions'
import { PERMISSION } from '@/constants/permissions'
import { useAuthStore } from '@/stores/auth'
import type { CompanyOut, UserOut } from '@/types/api'

function buildUser(overrides: Partial<UserOut> = {}): UserOut {
  return {
    id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    avatar: null,
    is_active: true,
    date_joined: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function buildCompany(myPermissions: string[]): CompanyOut {
  return {
    id: 1,
    name: 'Acme',
    slug: 'acme',
    my_permissions: myPermissions,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

describe('useCompanyPermissions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useAuthStore().currentUser = buildUser({ id: 1 })
  })

  it('answers the shortcuts from the permissions the API sent with the company', () => {
    const company = ref<CompanyOut | null>(
      buildCompany([PERMISSION.companyEdit, PERMISSION.companyMembers]),
    )

    const { canEditCompany, canManageMembers, canManagePipeline } = useCompanyPermissions(company)

    expect(canEditCompany.value).toBe(true)
    expect(canManageMembers.value).toBe(true)
    expect(canManagePipeline.value).toBe(false)
  })

  it('treats the pipeline separately from editing the company', () => {
    const { canEditCompany, canManagePipeline } = useCompanyPermissions(
      ref(buildCompany([PERMISSION.companyPipeline])),
    )

    expect(canManagePipeline.value).toBe(true)
    expect(canEditCompany.value).toBe(false)
  })

  it('grants nothing while there is no company', () => {
    const { can, canEditCompany, canManageMembers } = useCompanyPermissions(ref(null))

    expect(can(PERMISSION.companyEdit)).toBe(false)
    expect(canEditCompany.value).toBe(false)
    expect(canManageMembers.value).toBe(false)
  })

  it('grants nothing when the company came without permissions', () => {
    const company = ref<CompanyOut | null>({
      ...buildCompany([]),
      my_permissions: undefined,
    } as unknown as CompanyOut)

    const { canEditCompany } = useCompanyPermissions(company)

    expect(canEditCompany.value).toBe(false)
  })

  it('lets a member manager remove others but not themselves', () => {
    const { canRemoveMember, canChangeMemberRole } = useCompanyPermissions(
      ref(buildCompany([PERMISSION.companyMembers])),
    )

    expect(canRemoveMember(2)).toBe(true)
    expect(canChangeMemberRole(2)).toBe(true)
    expect(canRemoveMember(1)).toBe(false)
    expect(canChangeMemberRole(1)).toBe(false)
  })
})
