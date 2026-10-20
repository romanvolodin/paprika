import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import ProjectLayoutView from '@/views/ProjectLayoutView.vue'
import { useAuthStore } from '@/stores/auth'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import * as projectsApi from '@/api/projects'
import type { ProjectMemberOut, ProjectMembershipRole, ProjectOut } from '@/types/api'

vi.mock('@/api/projects')

const Empty = defineComponent({ render: () => h('div', { 'data-test': 'child' }) })

function buildProject(): ProjectOut {
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
  }
}

function buildMember(role: ProjectMembershipRole): ProjectMemberOut {
  return {
    id: 1,
    user_id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    role,
    created_at: '2026-01-01T00:00:00Z',
  }
}

async function mountLayout(
  role: ProjectMembershipRole,
  path = '/acme/PRJ/shots',
  projects: ProjectOut[] = [buildProject()],
) {
  vi.mocked(projectsApi.listProjects).mockResolvedValue({
    items: projects,
    total: projects.length,
    page: 1,
    page_size: 1,
  })
  vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({ items: [buildMember(role)] })

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/:companySlug/:projectCode',
        component: ProjectLayoutView,
        props: (route) => ({
          companySlug: String(route.params.companySlug),
          projectCode: String(route.params.projectCode),
        }),
        children: [
          { path: 'shots', name: 'shot-list', component: Empty },
          { path: 'shots/:shotName', name: 'shot-detail', component: Empty },
          { path: 'tasks', name: 'project-tasks', component: Empty },
          { path: 'groups', name: 'project-groups', component: Empty },
          { path: 'settings', name: 'project-settings', component: Empty },
        ],
      },
    ],
  })
  router.push(path)
  await router.isReady()

  const wrapper = mount(RouterView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('ProjectLayoutView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()

    const auth = useAuthStore()
    auth.currentUser = {
      id: 1,
      email: 'a@paprika.dev',
      first_name: 'A',
      last_name: 'One',
      avatar: null,
      is_active: true,
      date_joined: '2026-01-01T00:00:00Z',
    }
    const currentCompany = useCurrentCompanyStore()
    currentCompany.companies = [
      {
        id: 7,
        name: 'Acme',
        slug: 'acme',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]
    currentCompany.selectCompany(7)
  })

  it('shows the project name and code with the section links', async () => {
    const wrapper = await mountLayout('admin')

    expect(wrapper.text()).toContain('Feature Film')
    expect(wrapper.text()).toContain('PRJ')
    const links = wrapper.findAll('a').map((link) => link.text())
    expect(links).toContain('Кадры')
    expect(links).toContain('Задачи')
    expect(links).toContain('Группы')
    expect(wrapper.find('[data-test="child"]').exists()).toBe(true)
  })

  it('has no feed link until the feed exists', async () => {
    const wrapper = await mountLayout('admin')

    expect(wrapper.findAll('a').map((link) => link.text())).not.toContain('Лента')
  })

  it.each(['admin', 'producer'] as const)('shows the settings link to a %s', async (role) => {
    const wrapper = await mountLayout(role)

    expect(wrapper.findAll('a').map((link) => link.text())).toContain('Настройки')
  })

  it.each(['coordinator', 'executor', 'freelancer', 'client'] as const)(
    'hides the settings link from a %s',
    async (role) => {
      const wrapper = await mountLayout(role)

      expect(wrapper.findAll('a').map((link) => link.text())).not.toContain('Настройки')
    },
  )

  it('keeps "Кадры" highlighted on the page of a single shot', async () => {
    const wrapper = await mountLayout('admin', '/acme/PRJ/shots/0010')

    const active = wrapper.findAll('a.project-page__link--active').map((link) => link.text())
    expect(active).toEqual(['Кадры'])
  })

  it.each([
    ['/acme/PRJ/tasks', 'Задачи'],
    ['/acme/PRJ/groups', 'Группы'],
    ['/acme/PRJ/settings', 'Настройки'],
    ['/acme/PRJ/shots', 'Кадры'],
  ])('highlights only the current section on %s', async (path, label) => {
    const wrapper = await mountLayout('admin', path)

    const active = wrapper.findAll('a.project-page__link--active').map((link) => link.text())
    expect(active).toEqual([label])
  })

  it('says the project is not found for an unknown company slug', async () => {
    const wrapper = await mountLayout('admin', '/nope/PRJ/shots')

    expect(wrapper.text()).toContain('Проект не найден')
    expect(wrapper.find('[data-test="child"]').exists()).toBe(false)
  })

  it('says the project is not found when no project has that code', async () => {
    const wrapper = await mountLayout('admin', '/acme/NOPE/shots', [])

    expect(wrapper.text()).toContain('Проект не найден')
    expect(wrapper.find('[data-test="child"]').exists()).toBe(false)
  })
})
