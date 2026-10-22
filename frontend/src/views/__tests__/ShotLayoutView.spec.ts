import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import ShotLayoutView from '@/views/ShotLayoutView.vue'
import { useAuthStore } from '@/stores/auth'
import { useCurrentCompanyStore } from '@/stores/currentCompany'
import * as projectsApi from '@/api/projects'
import * as shotsApi from '@/api/shots'
import type { ProjectMemberOut, ProjectMembershipRole, ProjectOut, ShotOut } from '@/types/api'

vi.mock('@/api/projects')
vi.mock('@/api/shots')

const Empty = defineComponent({ render: () => h('div', { 'data-test': 'child' }) })

const project: ProjectOut = {
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

const shot: ShotOut = {
  id: 5,
  project_id: 1,
  group_ids: [],
  status_id: 1,
  name: '0010',
  rec_timecode: null,
  duration: null,
  created_by: null,
  updated_by: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
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

async function mountShot(role: ProjectMembershipRole, path = '/acme/PRJ/shots/0010') {
  vi.mocked(projectsApi.listProjects).mockResolvedValue({
    items: [project],
    total: 1,
    page: 1,
    page_size: 1,
  })
  vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({ items: [buildMember(role)] })
  vi.mocked(shotsApi.listShots).mockResolvedValue({
    items: [shot],
    total: 1,
    page: 1,
    page_size: 1,
  })
  vi.mocked(shotsApi.listShotStatuses).mockResolvedValue({
    items: [
      {
        id: 1,
        company_id: 7,
        name: 'Не начат',
        color: '#cc3333',
        order: 1,
        is_default: true,
        created_by: null,
        updated_by: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 2,
        company_id: 7,
        name: 'В работе',
        color: '#3366cc',
        order: 2,
        is_default: false,
        created_by: null,
        updated_by: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ],
  })
  vi.mocked(shotsApi.listShotGroups).mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 100,
  })

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/:companySlug/:projectCode/shots/:shotName',
        component: ShotLayoutView,
        props: (route) => ({
          companySlug: String(route.params.companySlug),
          projectCode: String(route.params.projectCode),
          shotName: String(route.params.shotName),
        }),
        children: [
          { path: '', name: 'shot-detail', component: Empty },
          { path: 'tasks', name: 'shot-tasks', component: Empty },
          { path: 'versions', name: 'shot-versions', component: Empty },
          { path: 'upload', name: 'shot-upload', component: Empty },
          { path: 'settings', name: 'shot-settings', component: Empty },
        ],
      },
      { path: '/:companySlug/:projectCode/shots', name: 'shot-list', component: Empty },
    ],
  })
  router.push(path)
  await router.isReady()

  const Host = () =>
    h(NMessageProvider, null, {
      default: () => h(NDialogProvider, null, { default: () => h(RouterView) }),
    })
  const wrapper = mount(Host, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('ShotLayoutView', () => {
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

  it('shows the shot name, project code and the four section tabs', async () => {
    const wrapper = await mountShot('executor')

    expect(wrapper.find('h1').text()).toBe('0010')
    expect(wrapper.text()).toContain('PRJ')
    const tabs = wrapper.findAll('nav a').map((link) => link.text())
    expect(tabs).toEqual(['Просмотр', 'Задачи', 'Версии', 'Настройки'])
    expect(wrapper.find('[data-test="child"]').exists()).toBe(true)
  })

  it('has the project code as a link back to the shot list in the same strip', async () => {
    const wrapper = await mountShot('executor')

    const crumb = wrapper.find('a.shot-page__crumb')
    expect(crumb.text()).toBe('PRJ')
    expect(crumb.attributes('href')).toBe('/acme/PRJ/shots')
    expect(crumb.attributes('title')).toBe('Feature Film')
    expect(wrapper.findAll('nav').length).toBe(1)
  })

  it.each([
    ['/acme/PRJ/shots/0010', 'Просмотр'],
    ['/acme/PRJ/shots/0010/tasks', 'Задачи'],
    ['/acme/PRJ/shots/0010/versions', 'Версии'],
    ['/acme/PRJ/shots/0010/settings', 'Настройки'],
  ])('highlights only the current tab on %s', async (path, label) => {
    const wrapper = await mountShot('executor', path)

    const active = wrapper.findAll('a.shot-page__link--active').map((link) => link.text())
    expect(active).toEqual([label])
  })

  it('highlights no tab on the upload page', async () => {
    const wrapper = await mountShot('executor', '/acme/PRJ/shots/0010/upload')

    expect(wrapper.find('a.shot-page__link--active').exists()).toBe(false)
    expect(wrapper.find('h1').text()).toBe('0010')
  })

  it('lets a member who can write change the status from the header', async () => {
    vi.mocked(shotsApi.updateShot).mockResolvedValue({ ...shot, status_id: 2 })
    const wrapper = await mountShot('executor')

    expect(wrapper.find('.shot-page__status-select').exists()).toBe(true)
    const select = wrapper.findComponent({ name: 'Select' })
    select.vm.$emit('update:value', 2)
    await flushPromises()

    expect(shotsApi.updateShot).toHaveBeenCalledWith(5, { status_id: 2 })
  })

  it('shows the status read-only to a client', async () => {
    const wrapper = await mountShot('client')

    expect(wrapper.find('.shot-page__status-select').exists()).toBe(false)
    expect(wrapper.text()).toContain('Не начат')
  })

  it('says the shot is not found for an unknown company slug', async () => {
    const wrapper = await mountShot('executor', '/nope/PRJ/shots/0010')

    expect(wrapper.text()).toContain('Кадр не найден')
    expect(wrapper.find('nav').exists()).toBe(false)
  })
})
