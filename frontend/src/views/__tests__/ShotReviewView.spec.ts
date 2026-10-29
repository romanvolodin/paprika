import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import ShotReviewView from '@/views/ShotReviewView.vue'
import { useAuthStore } from '@/stores/auth'
import { useShotDetailStore } from '@/stores/shotDetail'
import * as versionsApi from '@/api/versions'
import type { VersionOut } from '@/types/api'
import { buildProjectFor, roleRefOf, type StarterRole } from './starterRoles'

vi.mock('@/api/versions')

function buildVersion(id: number, name: string): VersionOut {
  return {
    id,
    project_id: 1,
    shot_id: 5,
    name,
    type: 'video',
    source: `/media/${name}.mp4`,
    converted: null,
    thumb: null,
    width: 1920,
    height: 1080,
    duration: 96,
    fps: 24,
    codec: 'h264',
    file_size: 1000,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

const v2 = buildVersion(2, 'PRJ_0010_v02')
const v1 = buildVersion(1, 'PRJ_0010_v01')

const ChatStub = {
  props: ['shotId', 'canWrite'],
  template: '<div data-test="chat-section" :data-shot-id="shotId" :data-can-write="canWrite" />',
}

async function mountReview(role: StarterRole, path = '/shot') {
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
      { path: '/shot', component: ShotReviewView },
      { path: '/shot/upload', name: 'shot-upload', component: { render: () => null } },
    ],
  })
  router.push(path)
  await router.isReady()

  const wrapper = mount(ShotReviewView, {
    global: { plugins: [router], stubs: { ShotChatSection: ChatStub } },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('ShotReviewView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(versionsApi.listVersions).mockResolvedValue({
      items: [v2, v1],
      total: 2,
      page: 1,
      page_size: 100,
    })
  })

  it('has the player and the versions strip on the left and the chat on the right', async () => {
    const { wrapper } = await mountReview('executor')

    expect(wrapper.find('[data-test="player"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="versions-strip"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="chat"] [data-test="chat-section"]').exists()).toBe(true)
  })

  it('gives the chat the shot and lets a member who can write post', async () => {
    const chat = (await mountReview('executor')).wrapper.find('[data-test="chat-section"]')

    expect(chat.attributes('data-shot-id')).toBe('5')
    expect(chat.attributes('data-can-write')).toBe('true')
  })

  it('makes the chat read-only for a client', async () => {
    const chat = (await mountReview('readonly')).wrapper.find('[data-test="chat-section"]')

    expect(chat.attributes('data-can-write')).toBe('false')
  })

  it('leads the upload tile of the strip to the upload page', async () => {
    const { wrapper } = await mountReview('executor')

    expect(wrapper.find('.versions-strip__upload').attributes('href')).toBe('/shot/upload')
  })

  it('plays the newest version when the address names none', async () => {
    const { wrapper } = await mountReview('executor')

    expect(wrapper.find('video').attributes('src')).toBe('/media/PRJ_0010_v02.mp4')
  })

  it('plays the version named in the address', async () => {
    const { wrapper } = await mountReview('executor', '/shot?version=PRJ_0010_v01')

    expect(wrapper.find('video').attributes('src')).toBe('/media/PRJ_0010_v01.mp4')
  })

  it('switches the player when the version in the address changes', async () => {
    const { wrapper, router } = await mountReview('executor')

    await router.push({ path: '/shot', query: { version: 'PRJ_0010_v01' } })
    await flushPromises()

    expect(wrapper.find('video').attributes('src')).toBe('/media/PRJ_0010_v01.mp4')
    expect(versionsApi.listVersions).toHaveBeenCalledTimes(1)
  })

  it('says so when the version in the address does not exist', async () => {
    const { wrapper } = await mountReview('executor', '/shot?version=PRJ_0010_v99')

    expect(wrapper.find('[data-test="player"]').text()).toBe('Версия PRJ_0010_v99 не найдена.')
  })

  it('shows every version in the strip and frames the one being played', async () => {
    const { wrapper } = await mountReview('executor', '/shot?version=PRJ_0010_v01')

    const items = wrapper.findAll('.versions-strip__item')
    expect(items.map((item) => item.text())).toEqual(['PRJ_0010_v02', 'PRJ_0010_v01'])
    expect(wrapper.find('[aria-current="true"]').text()).toBe('PRJ_0010_v01')
  })

  it('plays the version whose thumbnail is clicked and puts its name in the address', async () => {
    const { wrapper, router } = await mountReview('executor')

    await wrapper.findAll('.versions-strip__item')[1].trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.version).toBe('PRJ_0010_v01')
    expect(wrapper.find('video').attributes('src')).toBe('/media/PRJ_0010_v01.mp4')
  })
})
