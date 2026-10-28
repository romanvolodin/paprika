import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NMessageProvider } from 'naive-ui'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import ShotUploadView from '@/views/ShotUploadView.vue'
import { useAuthStore } from '@/stores/auth'
import { useShotDetailStore } from '@/stores/shotDetail'
import * as tasksApi from '@/api/tasks'
import * as versionsApi from '@/api/versions'
import type { VersionOut } from '@/types/api'
import { buildProjectFor, roleRefOf, type StarterRole } from './starterRoles'

vi.mock('@/api/versions')
vi.mock('@/api/tasks')

const created: VersionOut = {
  id: 20,
  project_id: 1,
  shot_id: 5,
  name: 'PRJ_0010_v02',
  type: 'video',
  source: 'http://localhost/media/a.mp4',
  converted: null,
  thumb: null,
  width: 1920,
  height: 1080,
  duration: 240,
  fps: 24,
  codec: 'h264',
  file_size: 1024,
  created_by: null,
  updated_by: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

async function mountUpload(role: StarterRole) {
  useAuthStore().currentUser = {
    id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    avatar: null,
    is_active: true,
    date_joined: '2026-01-01T00:00:00Z',
  }
  const store = useShotDetailStore()
  store.project = buildProjectFor(role)
  store.shot = {
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
  store.members = [
    {
      id: 1,
      user_id: 1,
      email: 'a@paprika.dev',
      first_name: 'A',
      last_name: 'One',
      role: roleRefOf(role),
      created_at: '2026-01-01T00:00:00Z',
    },
  ]

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/:companySlug/:projectCode/shots/:shotName/upload', component: ShotUploadView },
      {
        path: '/:companySlug/:projectCode/shots/:shotName',
        name: 'shot-detail',
        component: { render: () => h('div', { 'data-test': 'review' }) },
      },
    ],
  })
  router.push('/acme/PRJ/shots/0010/upload')
  await router.isReady()

  const Host = () => h(NMessageProvider, null, { default: () => h(RouterView) })
  const wrapper = mount(defineComponent({ render: Host }), { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

describe('ShotUploadView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    URL.createObjectURL = vi.fn(() => 'blob:preview')
    URL.revokeObjectURL = vi.fn()
    vi.mocked(tasksApi.listShotTasks).mockResolvedValue({ items: [] } as never)
    vi.mocked(tasksApi.listTaskTypes).mockResolvedValue({ items: [] } as never)
    vi.mocked(tasksApi.listTaskStatuses).mockResolvedValue({ items: [] } as never)
    vi.mocked(versionsApi.listVersions).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    })
  })

  it('offers the upload to a member who can write', async () => {
    const { wrapper } = await mountUpload('executor')

    expect(wrapper.find('h2').text()).toBe('Загрузить версию')
    expect(wrapper.find('input[type="file"]').exists()).toBe(true)
  })

  it('tells a client they cannot upload', async () => {
    const { wrapper } = await mountUpload('client')

    expect(wrapper.find('input[type="file"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('нет прав загружать версии')
  })

  it('goes to the player with the uploaded version once the upload is done', async () => {
    vi.mocked(versionsApi.uploadVersion).mockResolvedValue(created)
    const { wrapper, router } = await mountUpload('executor')
    const input = wrapper.find('input[type="file"]')
    const file = new File(['x'], 'PRJ_0010_v02.mp4', { type: 'video/mp4' })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })

    await input.trigger('change')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Отправить версию')!
      .trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('shot-detail')
    expect(router.currentRoute.value.path).toBe('/acme/PRJ/shots/0010')
    expect(router.currentRoute.value.query.version).toBe('PRJ_0010_v02')
  })
})
