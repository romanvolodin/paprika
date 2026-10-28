import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as companiesApi from '@/api/companies'
import * as rolesApi from '@/api/roles'
import type {
  CompanyMemberCreateIn,
  CompanyMemberOut,
  CompanyOut,
  CompanyUpdateIn,
  RoleOut,
} from '@/types/api'

export const useCompanyDetailStore = defineStore('companyDetail', () => {
  const company = ref<CompanyOut | null>(null)
  const members = ref<CompanyMemberOut[]>([])
  const roles = ref<RoleOut[]>([])
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
    isLoading,
    fetch,
    updateCompany,
    addMember,
    updateMemberRole,
    removeMember,
  }
})
