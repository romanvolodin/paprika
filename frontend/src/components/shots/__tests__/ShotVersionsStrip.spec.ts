import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import ShotVersionsStrip from '@/components/shots/ShotVersionsStrip.vue'
import type { VersionOut } from '@/types/api'

function buildVersion(id: number, name: string, thumb: string | null = `/media/${name}.jpg`) {
  return {
    id,
    project_id: 1,
    shot_id: 5,
    name,
    type: 'video',
    source: `/media/${name}.mp4`,
    converted: null,
    thumb,
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
  } satisfies VersionOut
}

const versions = [
  buildVersion(3, 'PRJ_0010_v03'),
  buildVersion(2, 'PRJ_0010_v02'),
  buildVersion(1, 'PRJ_0010_v01', null),
]

let router: Router

async function mountStrip(
  props: Partial<InstanceType<typeof ShotVersionsStrip>['$props']> = {},
  path = '/shot',
) {
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/shot', component: { render: () => null } },
      { path: '/shot/versions', name: 'shot-versions', component: { render: () => null } },
    ],
  })
  router.push(path)
  await router.isReady()

  return mount(ShotVersionsStrip, {
    props: {
      versions,
      currentId: 3,
      canWrite: true,
      uploadTo: { name: 'shot-versions' },
      ...props,
    },
    global: { plugins: [router] },
  })
}

describe('ShotVersionsStrip', () => {
  it('shows a tile with the name for every version, in the given order', async () => {
    const wrapper = await mountStrip()

    const names = wrapper.findAll('.versions-strip__item').map((item) => item.text())
    expect(names).toEqual(['PRJ_0010_v03', 'PRJ_0010_v02', 'PRJ_0010_v01'])
  })

  it('shows the thumbnail where there is one', async () => {
    const wrapper = await mountStrip()

    const tiles = wrapper.findAll('.versions-strip__item')
    expect(tiles[0].find('img').attributes('src')).toBe('/media/PRJ_0010_v03.jpg')
    expect(tiles[2].find('img').exists()).toBe(false)
  })

  it('frames only the version being played', async () => {
    const wrapper = await mountStrip({ currentId: 2 })

    const framed = wrapper.findAll('.versions-strip__item--active')
    expect(framed.map((item) => item.text())).toEqual(['PRJ_0010_v02'])
    expect(framed[0].attributes('aria-current')).toBe('true')
  })

  it('frames nothing when no version is being played', async () => {
    const wrapper = await mountStrip({ currentId: null })

    expect(wrapper.find('.versions-strip__item--active').exists()).toBe(false)
  })

  it('links each tile to the same page with its name in the address', async () => {
    const wrapper = await mountStrip({}, '/shot?other=1')

    const href = wrapper.findAll('.versions-strip__item')[1].attributes('href')
    expect(href).toBe('/shot?other=1&version=PRJ_0010_v02')
  })

  it('puts the version name in the address on a click', async () => {
    const wrapper = await mountStrip()

    await wrapper.findAll('.versions-strip__item')[2].trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.version).toBe('PRJ_0010_v01')
  })

  it('has the upload link first for a member who can write', async () => {
    const wrapper = await mountStrip()

    const upload = wrapper.find('.versions-strip__upload')
    expect(upload.text()).toBe('Загрузить версию')
    expect(upload.attributes('href')).toBe('/shot/versions')
    expect(wrapper.find('a').classes()).toContain('versions-strip__upload')
  })

  it('has no upload link for a client', async () => {
    const wrapper = await mountStrip({ canWrite: false })

    expect(wrapper.find('.versions-strip__upload').exists()).toBe(false)
  })
})
