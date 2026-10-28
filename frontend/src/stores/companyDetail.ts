import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as companiesApi from '@/api/companies'
import * as rolesApi from '@/api/roles'
import type {
  CompanyMemberCreateIn,
  CompanyMemberOut,
  CompanyOut,
  CompanyUpdateIn,
  PermissionOut,
  RoleCreateIn,
  RoleOut,
  RoleUpdateIn,
} from '@/types/api'

export const useCompanyDetailStore = defineStore('companyDetail', () => {
  const company = ref<CompanyOut | null>(null)
  const members = ref<CompanyMemberOut[]>([])
  const roles = ref<RoleOut[]>([])
  // The fixed list of permissions a role is made of, the same for every company.
  const permissionCatalog = ref<PermissionOut[]>([])
  const isLoading = ref(false)

  async function fetch(companyId: number) {
    isLoading.value = true
    try {
      const [companyResult, membersResult, rolesResult] = await Promise.all([
        companiesApi.getCompany(companyId),
        companiesApi.listCompanyMembers(companyId),
        rolesApi.listCompanyRoles(companyId),
      ])
      company.value = companyResult
      members.value = membersResult.items
      roles.value = rolesResult.items
    } finally {
      isLoading.value = false
    }
  }

  async function loadPermissionCatalog() {
    if (permissionCatalog.value.length > 0) return
    permissionCatalog.value = (await rolesApi.listPermissions()).items
  }

  async function refetchRoles(companyId: number) {
    roles.value = (await rolesApi.listCompanyRoles(companyId)).items
  }

  async function createRole(companyId: number, input: RoleCreateIn): Promise<RoleOut> {
    const role = await rolesApi.createRole(companyId, input)
    await refetchRoles(companyId)
    return role
  }

  async function updateRole(companyId: number, roleId: number, input: RoleUpdateIn) {
    await rolesApi.updateRole(roleId, input)
    await refetchRoles(companyId)
  }

  async function removeRole(companyId: number, roleId: number) {
    await rolesApi.deleteRole(roleId)
    await refetchRoles(companyId)
  }

  async function updateCompany(companyId: number, input: CompanyUpdateIn) {
    company.value = await companiesApi.updateCompany(companyId, input)
  }

  async function refetchMembers(companyId: number) {
    members.value = (await companiesApi.listCompanyMembers(companyId)).items
  }

  async function addMember(companyId: number, input: CompanyMemberCreateIn) {
    await companiesApi.addCompanyMember(companyId, input)
    await refetchMembers(companyId)
  }

  async function updateMemberRole(companyId: number, userId: number, roleId: number) {
    await companiesApi.updateCompanyMember(companyId, userId, { role_id: roleId })
    await refetchMembers(companyId)
  }

  async function removeMember(companyId: number, userId: number) {
    await companiesApi.removeCompanyMember(companyId, userId)
    await refetchMembers(companyId)
  }

  return {
    company,
    members,
    roles,
    permissionCatalog,
    isLoading,
    fetch,
    loadPermissionCatalog,
    createRole,
    updateRole,
    removeRole,
    updateCompany,
    addMember,
    updateMemberRole,
    removeMember,
  }
})
