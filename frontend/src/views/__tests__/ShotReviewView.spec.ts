import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ShotReviewView from '@/views/ShotReviewView.vue'
import { useAuthStore } from '@/stores/auth'
import { useShotDetailStore } from '@/stores/shotDetail'
import type { ProjectMembershipRole } from '@/types/api'

const ChatStub = {
  props: ['shotId', 'canWrite'],
  template: '<div data-test="chat-section" :data-shot-id="shotId" :data-can-write="canWrite" />',
}

function mountReview(role: ProjectMembershipRole) {
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
  const store = useShotDetailStore()
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
      role,
      created_at: '2026-01-01T00:00:00Z',
    },
  ]
  return mount(ShotReviewView, { global: { stubs: { ShotChatSection: ChatStub } } })
}

describe('ShotReviewView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('has the player and the versions strip on the left and the chat on the right', () => {
    const wrapper = mountReview('executor')

    expect(wrapper.find('[data-test="player"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="versions-strip"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="chat"] [data-test="chat-section"]').exists()).toBe(true)
  })

  it('gives the chat the shot and lets a member who can write post', () => {
    const chat = mountReview('executor').find('[data-test="chat-section"]')

    expect(chat.attributes('data-shot-id')).toBe('5')
    expect(chat.attributes('data-can-write')).toBe('true')
  })

  it('makes the chat read-only for a client', () => {
    const chat = mountReview('client').find('[data-test="chat-section"]')

    expect(chat.attributes('data-can-write')).toBe('false')
  })
})
