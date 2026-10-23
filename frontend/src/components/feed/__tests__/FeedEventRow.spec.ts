import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import FeedEventRow from '@/components/feed/FeedEventRow.vue'
import type { FeedItemOut } from '@/types/api'

const Empty = defineComponent({ render: () => h('div') })

const anna = {
  id: 2,
  email: 'anna@example.com',
  first_name: 'Анна',
  last_name: 'Смирнова',
  avatar: null,
  is_active: true,
  date_joined: '2026-01-01T00:00:00Z',
}

function buildItem(overrides: Partial<FeedItemOut>): FeedItemOut {
  return {
    key: 'chat-1',
    type: 'chat',
    created_at: '2026-10-21T10:00:00Z',
    created_by: anna,
    shot: { id: 1, name: 'PRJ_0010' },
    text: null,
    attachments: [],
    versions: [],
    version: null,
    event: null,
    payload: {},
    ...overrides,
  }
}

async function mountRow(item: FeedItemOut) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/:companySlug/:projectCode/shots/:shotName', name: 'shot-detail', component: Empty },
    ],
  })
  await router.push('/acme/PRJ/shots/PRJ_0010')
  return mount(FeedEventRow, {
    props: { item, companySlug: 'acme', projectCode: 'PRJ' },
    global: { plugins: [router] },
  })
}

describe('FeedEventRow', () => {
  it('shows a chat message with its author, shot link and text', async () => {
    const wrapper = await mountRow(buildItem({ text: 'Нужен интерфейс' }))

    expect(wrapper.text()).toContain('Анна Смирнова')
    expect(wrapper.text()).toContain('написал в чате')
    expect(wrapper.text()).toContain(': Нужен интерфейс')
    expect(wrapper.find('a').attributes('href')).toBe('/acme/PRJ/shots/PRJ_0010')
  })

  it('shows an uploaded version with a thumbnail that opens the file', async () => {
    const wrapper = await mountRow(
      buildItem({
        key: 'version-3',
        type: 'version',
        version: {
          id: 3,
          name: 'PRJ_0010_v02',
          type: 'video',
          source: 'http://x/source.mp4',
          converted: null,
          thumb: 'http://x/thumb.jpg',
        },
      }),
    )

    expect(wrapper.text()).toContain('загрузил версию')
    const links = wrapper.findAll('a')
    expect(links[0]!.text()).toBe('PRJ_0010_v02')
    expect(links[0]!.attributes('href')).toBe('/acme/PRJ/shots/PRJ_0010?version=PRJ_0010_v02')
    expect(links[1]!.attributes('href')).toBe('http://x/source.mp4')
    expect(links[1]!.find('img').attributes('src')).toBe('http://x/thumb.jpg')
  })

  it('describes a task event and names the shot', async () => {
    const wrapper = await mountRow(
      buildItem({
        key: 'task-4',
        type: 'task',
        event: 'status_changed',
        payload: {
          task_code: 'CLN1234',
          from: { id: 1, name: 'Не начата' },
          to: { id: 2, name: 'В работе' },
        },
      }),
    )

    expect(wrapper.text()).toContain('сменил статус задачи CLN1234: Не начата → В работе')
    expect(wrapper.find('a').text()).toBe('PRJ_0010')
  })

  it('shows "Кто-то" for a deleted author', async () => {
    const wrapper = await mountRow(buildItem({ created_by: null, text: 'Привет' }))

    expect(wrapper.text()).toContain('Кто-то')
  })
})
