import { ref } from 'vue'
import { defineStore } from 'pinia'
import { isAxiosError } from 'axios'
import * as companiesApi from '@/api/companies'
import * as projectsApi from '@/api/projects'
import * as rolesApi from '@/api/roles'
import type { UpdateProjectInput } from '@/api/projects'
import type {
  CompanyMemberOut,
  CompanyOut,
  ProjectMemberCreateIn,
  ProjectMemberOut,
  ProjectOut,
  RoleOut,
} from '@/types/api'

export type ProjectPageState = 'loading' | 'ready' | 'not-found' | 'error'

export const useProjectPageStore = defineStore('projectPage', () => {
  const state = ref<ProjectPageState>('loading')
  const company = ref<CompanyOut | null>(null)
  const project = ref<ProjectOut | null>(null)
  const members = ref<ProjectMemberOut[]>([])
  // Only an existing company member can be added to the project (see
  // apps/projects/api/views.py), so the settings page builds its "add
  // member" picker from this list instead of a system-wide user search.
  const companyMembers = ref<CompanyMemberOut[]>([])
  // The company's roles, for the role pickers of the members list.
  const roles = ref<RoleOut[]>([])
  const isLoading = ref(false)

  // `open` can be called again (another project, another company) while
  // an earlier call is still in flight - only the latest one may write.
  let openToken = 0

  /**
   * Resolve the project from its company-unique code (the API only
   * knows numeric ids, so the code goes through the project list's
   * exact `code` filter) and load its members.
   */
  async function open(target: CompanyOut, projectCode: string) {
    const token = ++openToken
    state.value = 'loading'
    company.value = target
    project.value = null
    members.value = []
    companyMembers.value = []
    roles.value = []

    try {
      const candidates = await projectsApi.listProjects(target.id, {
        code: projectCode,
        page_size: 1,
      })
      const found = candidates.items[0]
      if (token !== openToken) return
      if (!found) {
        state.value = 'not-found'
        return
      }

      const memberList = await projectsApi.listProjectMembers(found.id)
      if (token !== openToken) return
      project.value = found
      members.value = memberList.items
      state.value = 'ready'
    } catch (error) {
      if (token !== openToken) return
      state.value = isAxiosError(error) && error.response?.status === 404 ? 'not-found' : 'error'
    }
  }

  function setNotFound() {
    openToken++
    company.value = null
    project.value = null
    members.value = []
    companyMembers.value = []
    roles.value = []
    state.value = 'not-found'
  }

  async function loadCompanyMembers() {
    if (!project.value) return
    isLoading.value = true
    try {
      const [membersResult, rolesResult] = await Promise.all([
        companiesApi.listCompanyMembers(project.value.company_id),
        rolesApi.listCompanyRoles(project.value.company_id),
      ])
      companyMembers.value = membersResult.items
      roles.value = rolesResult.items
    } finally {
      isLoading.value = false
    }
  }

  async function updateProject(input: UpdateProjectInput) {
    if (!project.value) return
    project.value = await projectsApi.updateProject(project.value.id, input)
  }

  async function deleteProject() {
    if (!project.value) return
    await projectsApi.deleteProject(project.value.id)
  }

  async function refetchMembers() {
    if (!project.value) return
    members.value = (await projectsApi.listProjectMembers(project.value.id)).items
  }

  async function addMember(input: ProjectMemberCreateIn) {
    if (!project.value) return
    await projectsApi.addProjectMember(project.value.id, input)
    await refetchMembers()
  }

  async function updateMemberRole(userId: number, roleId: number) {
    if (!project.value) return
    await projectsApi.updateProjectMember(project.value.id, userId, { role_id: roleId })
    await refetchMembers()
  }

  async function removeMember(userId: number) {
    if (!project.value) return
    await projectsApi.removeProjectMember(project.value.id, userId)
    await refetchMembers()
  }

  return {
    state,
    company,
    project,
    members,
    companyMembers,
    roles,
    isLoading,
    open,
    setNotFound,
    loadCompanyMembers,
    updateProject,
    deleteProject,
    refetchMembers,
    addMember,
    updateMemberRole,
    removeMember,
  }
})
