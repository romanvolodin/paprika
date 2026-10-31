import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AxiosError } from 'axios'
import { useProjectPageStore } from '@/stores/projectPage'
import * as companiesApi from '@/api/companies'
import * as invitationsApi from '@/api/invitations'
import * as projectsApi from '@/api/projects'
import * as rolesApi from '@/api/roles'
import type {
  CompanyMemberOut,
  CompanyOut,
  ProjectMemberOut,
  ProjectOut,
  RoleOut,
  RoleRefOut,
} from '@/types/api'

vi.mock('@/api/projects')
vi.mock('@/api/companies')
vi.mock('@/api/roles')
vi.mock('@/api/invitations')

const company: CompanyOut = {
  id: 7,
  name: 'Acme',
  slug: 'acme',
  my_permissions: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

function buildRole(overrides: Partial<RoleRefOut> = {}): RoleRefOut {
  return { id: 1, name: 'Админ', color: '#00A64F', ...overrides }
}

function buildRoleOut(overrides: Partial<RoleOut> = {}): RoleOut {
  return {
    id: 1,
    company_id: 7,
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

function buildProject(overrides: Partial<ProjectOut> = {}): ProjectOut {
  return {
    id: 1,
    company_id: 7,
    name: 'Feature Film',
    code: 'PRJ',
    description: '',
    cover: null,
    start_date: null,
    deadline: null,
    is_active: true,
    my_permissions: [],
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function buildMember(overrides: Partial<ProjectMemberOut> = {}): ProjectMemberOut {
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

function buildCompanyMember(overrides: Partial<CompanyMemberOut> = {}): CompanyMemberOut {
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

function listOf(items: ProjectOut[]) {
  return { items, total: items.length, page: 1, page_size: 1 }
}

async function openedStore() {
  vi.mocked(projectsApi.listProjects).mockResolvedValue(listOf([buildProject()]))
  vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({ items: [buildMember()] })
  const store = useProjectPageStore()
  await store.open(company, 'PRJ')
  return store
}

describe('useProjectPageStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(rolesApi.listCompanyRoles).mockResolvedValue({ items: [] })
  })

  describe('open', () => {
    it('resolves the project by its code and loads its members', async () => {
      const store = await openedStore()

      expect(projectsApi.listProjects).toHaveBeenCalledWith(7, { code: 'PRJ', page_size: 1 })
      expect(projectsApi.listProjectMembers).toHaveBeenCalledWith(1)
      expect(store.project).toEqual(buildProject())
      expect(store.members).toHaveLength(1)
      expect(store.state).toBe('ready')
    })

    it('is not-found when no project has that code', async () => {
      vi.mocked(projectsApi.listProjects).mockResolvedValue(listOf([]))

      const store = useProjectPageStore()
      await store.open(company, 'NOPE')

      expect(store.state).toBe('not-found')
      expect(store.project).toBeNull()
      expect(projectsApi.listProjectMembers).not.toHaveBeenCalled()
    })

    it('is not-found when the API answers 404', async () => {
      vi.mocked(projectsApi.listProjects).mockResolvedValue(listOf([buildProject()]))
      vi.mocked(projectsApi.listProjectMembers).mockRejectedValue(
        new AxiosError('nope', '404', undefined, undefined, {
          status: 404,
        } as never),
      )

      const store = useProjectPageStore()
      await store.open(company, 'PRJ')

      expect(store.state).toBe('not-found')
    })

    it('is an error on any other failure', async () => {
      vi.mocked(projectsApi.listProjects).mockRejectedValue(new Error('boom'))

      const store = useProjectPageStore()
      await store.open(company, 'PRJ')

      expect(store.state).toBe('error')
    })

    it('ignores the result of an earlier open that finished late', async () => {
      let resolveFirst!: (value: ReturnType<typeof listOf>) => void
      vi.mocked(projectsApi.listProjects)
        .mockReturnValueOnce(
          new Promise((resolve) => {
            resolveFirst = resolve
          }),
        )
        .mockResolvedValueOnce(listOf([buildProject({ id: 2, code: 'SEC' })]))
      vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({ items: [] })

      const store = useProjectPageStore()
      const first = store.open(company, 'PRJ')
      await store.open(company, 'SEC')
      resolveFirst(listOf([buildProject()]))
      await first

      expect(store.project?.code).toBe('SEC')
    })
  })

  describe('setNotFound', () => {
    it('drops the loaded project', async () => {
      const store = await openedStore()

      store.setNotFound()

      expect(store.state).toBe('not-found')
      expect(store.project).toBeNull()
      expect(store.members).toEqual([])
    })
  })

  describe('loadCompanyMembers', () => {
    it("loads the members of the project's company", async () => {
      const store = await openedStore()
      vi.mocked(companiesApi.listCompanyMembers).mockResolvedValue({
        items: [buildCompanyMember(), buildCompanyMember({ user_id: 2 })],
      })

      vi.mocked(rolesApi.listCompanyRoles).mockResolvedValue({
        items: [buildRoleOut(), buildRoleOut({ id: 4, name: 'Исполнитель' })],
      })

      await store.loadCompanyMembers()

      expect(companiesApi.listCompanyMembers).toHaveBeenCalledWith(7)
      expect(rolesApi.listCompanyRoles).toHaveBeenCalledWith(7)
      expect(store.companyMembers).toHaveLength(2)
      expect(store.roles.map((role) => role.name)).toEqual(['Админ', 'Исполнитель'])
      expect(store.isLoading).toBe(false)
    })
  })

  describe('inviteToProject', () => {
    it('invites to the open project and returns the invitation', async () => {
      const store = await openedStore()
      const sent = { id: 3, token: 'tok' } as never
      vi.mocked(invitationsApi.createProjectInvitation).mockResolvedValue(sent)

      const result = await store.inviteToProject({ email: 'new@paprika.dev', role_id: 4 })

      expect(invitationsApi.createProjectInvitation).toHaveBeenCalledWith(1, {
        email: 'new@paprika.dev',
        role_id: 4,
      })
      expect(result).toBe(sent)
    })

    it('refuses when no project is open', async () => {
      const store = useProjectPageStore()

      await expect(store.inviteToProject({ email: 'a@b.dev', role_id: 4 })).rejects.toThrow()
    })
  })

  describe('updateProject', () => {
    it('replaces the local project with the server response', async () => {
      const store = await openedStore()
      vi.mocked(projectsApi.updateProject).mockResolvedValue(buildProject({ name: 'Renamed' }))

      await store.updateProject({ name: 'Renamed' })

      expect(projectsApi.updateProject).toHaveBeenCalledWith(1, { name: 'Renamed' })
      expect(store.project?.name).toBe('Renamed')
    })
  })

  describe('deleteProject', () => {
    it('deletes the open project', async () => {
      const store = await openedStore()
      vi.mocked(projectsApi.deleteProject).mockResolvedValue(
        undefined as unknown as Awaited<ReturnType<typeof projectsApi.deleteProject>>,
      )

      await store.deleteProject()

      expect(projectsApi.deleteProject).toHaveBeenCalledWith(1)
    })

    it('propagates the failure so the page can show it', async () => {
      const store = await openedStore()
      vi.mocked(projectsApi.deleteProject).mockRejectedValue(new Error('403'))

      await expect(store.deleteProject()).rejects.toThrow('403')
    })
  })

  describe('addMember', () => {
    it('adds the member then refetches the members list', async () => {
      const store = await openedStore()
      vi.mocked(projectsApi.addProjectMember).mockResolvedValue(buildMember())
      vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({
        items: [buildMember(), buildMember({ user_id: 2 })],
      })

      await store.addMember({ user_id: 2, role_id: 4 })

      expect(projectsApi.addProjectMember).toHaveBeenCalledWith(1, {
        user_id: 2,
        role_id: 4,
      })
      expect(store.members).toHaveLength(2)
    })
  })

  describe('updateMemberRole', () => {
    it('updates the role then refetches the members list', async () => {
      const store = await openedStore()
      vi.mocked(projectsApi.updateProjectMember).mockResolvedValue(
        buildMember({ role: buildRole({ id: 3, name: 'Координатор' }) }),
      )
      vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({
        items: [buildMember({ role: buildRole({ id: 3, name: 'Координатор' }) })],
      })

      await store.updateMemberRole(1, 3)

      expect(projectsApi.updateProjectMember).toHaveBeenCalledWith(1, 1, { role_id: 3 })
      expect(store.members[0]?.role.name).toBe('Координатор')
    })
  })

  describe('removeMember', () => {
    it('removes the member then refetches the members list', async () => {
      const store = await openedStore()
      vi.mocked(projectsApi.removeProjectMember).mockResolvedValue(
        undefined as unknown as Awaited<ReturnType<typeof projectsApi.removeProjectMember>>,
      )
      vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({ items: [] })

      await store.removeMember(1)

      expect(projectsApi.removeProjectMember).toHaveBeenCalledWith(1, 1)
      expect(store.members).toHaveLength(0)
    })
  })
})
