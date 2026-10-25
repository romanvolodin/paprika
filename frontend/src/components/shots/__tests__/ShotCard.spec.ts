import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ShotCard from '@/components/shots/ShotCard.vue'
import type { ShotGroupOut, ShotOut, ShotStatusOut } from '@/types/api'

function buildShot(overrides: Partial<ShotOut> = {}): ShotOut {
  return {
    id: 5,
    project_id: 1,
    group_ids: [],
    status_id: 3,
    name: 'PRJ_0010',
    rec_timecode: null,
    duration: null,
    thumb: 'http://localhost/media/PRJ_0010_v02.jpg',
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const status = {
  id: 3,
  company_id: 1,
  name: 'В работе',
  color: '#e8a33d',
  order: 1,
  is_default: false,
} as ShotStatusOut

const groups = [
  { id: 1, project_id: 1, name: 'Эпизод 1' },
  { id: 2, project_id: 1, name: 'Эпизод 2' },
] as ShotGroupOut[]

async function mountCard(props: {
  shot?: ShotOut
  status?: ShotStatusOut
  groups?: ShotGroupOut[]
}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/shots/:name', name: 'shot', component: { render: () => null } }],
  })
  router.push('/shots/PRJ_0010')
  await router.isReady()
  return mount(ShotCard, {
    props: {
      shot: buildShot(),
      groups: [],
      to: { name: 'shot', params: { name: 'PRJ_0010' } },
      ...props,
    },
    global: { plugins: [router] },
  })
}

describe('ShotCard', () => {
  it('links to the shot and shows its name, status and preview', async () => {
    const wrapper = await mountCard({ status })

    expect(wrapper.get('a').attributes('href')).toBe('/shots/PRJ_0010')
    expect(wrapper.text()).toContain('PRJ_0010')
    expect(wrapper.text()).toContain('В работе')
    expect(wrapper.get('img').attributes('src')).toBe('http://localhost/media/PRJ_0010_v02.jpg')
  })

  it('shows a placeholder instead of the preview when the shot has none', async () => {
    const wrapper = await mountCard({ shot: buildShot({ thumb: null }) })

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('Нет превью')
  })

  it('shows the groups of the shot', async () => {
    const wrapper = await mountCard({ groups })

    expect(wrapper.text()).toContain('Эпизод 1')
    expect(wrapper.text()).toContain('Эпизод 2')
  })

  it('shows no status when it is unknown', async () => {
    const wrapper = await mountCard({})

    expect(wrapper.text()).not.toContain('В работе')
  })
})
