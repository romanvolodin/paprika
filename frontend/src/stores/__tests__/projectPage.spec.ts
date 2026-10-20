import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AxiosError } from 'axios'
import { useProjectPageStore } from '@/stores/projectPage'
import * as companiesApi from '@/api/companies'
import * as projectsApi from '@/api/projects'
import type { CompanyMemberOut, CompanyOut, ProjectMemberOut, ProjectOut } from '@/types/api'

vi.mock('@/api/projects')
vi.mock('@/api/companies')

const company: CompanyOut = {
  id: 7,
  name: 'Acme',
  slug: 'acme',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
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
    role: 'admin',
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
    role: 'admin',
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

      await store.loadCompanyMembers()

      expect(companiesApi.listCompanyMembers).toHaveBeenCalledWith(7)
      expect(store.companyMembers).toHaveLength(2)
      expect(store.isLoading).toBe(false)
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

      await store.addMember({ user_id: 2, role: 'executor' })

      expect(projectsApi.addProjectMember).toHaveBeenCalledWith(1, {
        user_id: 2,
        role: 'executor',
      })
      expect(store.members).toHaveLength(2)
    })
  })

  describe('updateMemberRole', () => {
    it('updates the role then refetches the members list', async () => {
      const store = await openedStore()
      vi.mocked(projectsApi.updateProjectMember).mockResolvedValue(
        buildMember({ role: 'coordinator' }),
      )
      vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({
        items: [buildMember({ role: 'coordinator' })],
      })

      await store.updateMemberRole(1, 'coordinator')

      expect(projectsApi.updateProjectMember).toHaveBeenCalledWith(1, 1, { role: 'coordinator' })
      expect(store.members[0]?.role).toBe('coordinator')
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
