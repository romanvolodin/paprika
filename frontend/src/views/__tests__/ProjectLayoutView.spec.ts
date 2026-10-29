import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import ProjectLayoutView from '@/views/ProjectLayoutView.vue'
import { useAuthStore } from '@/stores/auth'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import * as projectsApi from '@/api/projects'
import type { ProjectMemberOut, ProjectOut } from '@/types/api'
import { buildProjectFor, roleRefOf, type StarterRole } from './starterRoles'

vi.mock('@/api/projects')

const Empty = defineComponent({ render: () => h('div', { 'data-test': 'child' }) })

function buildMember(role: StarterRole): ProjectMemberOut {
  return {
    id: 1,
    user_id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    role: roleRefOf(role),
    created_at: '2026-01-01T00:00:00Z',
  }
}

async function mountLayout(
  role: StarterRole,
  path = '/acme/PRJ/shots',
  projects: ProjectOut[] = [buildProjectFor(role)],
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
          { path: 'shots/import', name: 'shot-import', component: Empty },
          { path: 'shots/:shotName', name: 'shot-detail', component: Empty },
          { path: 'shots/:shotName/tasks', name: 'shot-tasks', component: Empty },
          { path: 'shots/:shotName/versions', name: 'shot-versions', component: Empty },
          { path: 'shots/:shotName/upload', name: 'shot-upload', component: Empty },
          { path: 'shots/:shotName/settings', name: 'shot-settings', component: Empty },
          { path: 'feed', name: 'project-feed', component: Empty },
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
      is_superuser: false,
      must_change_password: false,
    }
    const currentCompany = useCurrentCompanyStore()
    currentCompany.companies = [
      {
        id: 7,
        name: 'Acme',
        slug: 'acme',
        my_permissions: [],
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
    expect(links).toContain('Лента')
    expect(links).toContain('Кадры')
    expect(links).toContain('Задачи')
    expect(links).toContain('Группы')
    expect(wrapper.find('[data-test="child"]').exists()).toBe(true)
  })

  it('puts the settings link in the same group as the other sections', async () => {
    const wrapper = await mountLayout('admin')

    const nav = wrapper.find('nav[aria-label="Разделы проекта"]')
    expect(nav.findAll('a').map((link) => link.text())).toEqual([
      'Лента',
      'Кадры',
      'Задачи',
      'Группы',
      'Настройки',
    ])
  })

  it.each(['admin', 'producer', 'coordinator'] as const)(
    'shows the settings link to a %s',
    async (role) => {
      const wrapper = await mountLayout(role)

      expect(wrapper.findAll('a').map((link) => link.text())).toContain('Настройки')
    },
  )

  it.each(['executor', 'freelancer', 'client'] as const)(
    'hides the settings link from a %s',
    async (role) => {
      const wrapper = await mountLayout(role)

      expect(wrapper.findAll('a').map((link) => link.text())).not.toContain('Настройки')
    },
  )

  it.each(['', '/tasks', '/versions', '/upload', '/settings'])(
    'hides the project header on the shot page %s',
    async (suffix) => {
      const wrapper = await mountLayout('admin', `/acme/PRJ/shots/0010${suffix}`)

      expect(wrapper.find('nav').exists()).toBe(false)
      expect(wrapper.find('[data-test="child"]').exists()).toBe(true)
    },
  )

  it('keeps "Кадры" highlighted on the import page', async () => {
    const wrapper = await mountLayout('admin', '/acme/PRJ/shots/import')

    const active = wrapper.findAll('a.project-page__link--active').map((link) => link.text())
    expect(active).toEqual(['Кадры'])
  })

  it.each([
    ['/acme/PRJ/feed', 'Лента'],
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
