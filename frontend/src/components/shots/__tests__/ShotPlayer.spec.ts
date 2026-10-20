import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ShotPlayer from '@/components/shots/ShotPlayer.vue'
import type { VersionOut } from '@/types/api'

function buildVersion(overrides: Partial<VersionOut> = {}): VersionOut {
  return {
    id: 1,
    project_id: 1,
    shot_id: 5,
    name: 'PRJ_0010_v01',
    type: 'video',
    source: '/media/source.mp4',
    converted: null,
    thumb: '/media/thumb.jpg',
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
    ...overrides,
  }
}

function mountPlayer(props: Partial<InstanceType<typeof ShotPlayer>['$props']> = {}) {
  return mount(ShotPlayer, {
    props: { state: 'ready', version: buildVersion(), requestedName: null, ...props },
  })
}

describe('ShotPlayer', () => {
  it('plays a video muted, in a loop, with the browser controls and the thumbnail as poster', () => {
    const video = mountPlayer().find('video')

    expect(video.exists()).toBe(true)
    expect(video.attributes('src')).toBe('/media/source.mp4')
    expect(video.attributes('poster')).toBe('/media/thumb.jpg')
    expect(video.attributes('autoplay')).toBeDefined()
    expect(video.attributes('controls')).toBeDefined()
    expect(video.attributes('loop')).toBeDefined()
    expect((video.element as HTMLVideoElement).muted).toBe(true)
  })

  it('prefers the converted file over the source', () => {
    const video = mountPlayer({
      version: buildVersion({ converted: '/media/converted.mp4' }),
    }).find('video')

    expect(video.attributes('src')).toBe('/media/converted.mp4')
  })

  it('shows an image version as a picture', () => {
    const wrapper = mountPlayer({
      version: buildVersion({ type: 'image', source: '/media/frame.png', thumb: null }),
    })

    expect(wrapper.find('video').exists()).toBe(false)
    expect(wrapper.find('img').attributes('src')).toBe('/media/frame.png')
  })

  it('starts a new video element when the version changes', async () => {
    const wrapper = mountPlayer()
    const first = wrapper.find('video').element

    await wrapper.setProps({ version: buildVersion({ id: 2, source: '/media/other.mp4' }) })

    expect(wrapper.find('video').element).not.toBe(first)
  })

  it.each([
    ['loading', 'Загрузка…'],
    ['empty', 'В кадре пока нет версий.'],
    ['error', 'Не удалось загрузить версии.'],
  ] as const)('shows a note in the %s state', (state, text) => {
    const wrapper = mountPlayer({ state, version: null })

    expect(wrapper.text()).toBe(text)
    expect(wrapper.find('video').exists()).toBe(false)
  })

  it('names the version that was not found', () => {
    const wrapper = mountPlayer({
      state: 'not-found',
      version: null,
      requestedName: 'PRJ_0010_v99',
    })

    expect(wrapper.text()).toBe('Версия PRJ_0010_v99 не найдена.')
  })
})
