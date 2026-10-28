import { computed, type Ref } from 'vue'
import { useMembershipPermissions } from './useMembershipPermissions'
import { PERMISSION, type PermissionCode } from '@/constants/permissions'
import type { CompanyOut } from '@/types/api'

/**
 * What the current user may do in the company, from the `my_permissions`
 * the API sends with it. See `useMembershipPermissions` for the members
 * list rules.
 */
export function useCompanyPermissions(company: Ref<CompanyOut | null>) {
  function can(code: PermissionCode): boolean {
    return company.value?.my_permissions?.includes(code) ?? false
  }

  const canEditCompany = computed(() => can(PERMISSION.companyEdit))
  const canManagePipeline = computed(() => can(PERMISSION.companyPipeline))
  const canManageMembers = computed(() => can(PERMISSION.companyMembers))
  const canManageRoles = computed(() => can(PERMISSION.companyRoles))

  return {
    can,
    canEditCompany,
    canManagePipeline,
    canManageRoles,
    ...useMembershipPermissions(canManageMembers),
  }
}
