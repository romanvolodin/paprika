import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NMessageProvider } from 'naive-ui'
import ShotVersionUpload from '@/components/shots/ShotVersionUpload.vue'
import { useVersionsStore } from '@/stores/versions'
import * as versionsApi from '@/api/versions'
import type { VersionOut } from '@/types/api'

vi.mock('@/api/versions')

const created: VersionOut = {
  id: 20,
  project_id: 1,
  shot_id: 10,
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

const received: VersionOut[] = []

const Host = defineComponent({
  setup() {
    return () =>
      h(NMessageProvider, null, {
        default: () =>
          h(ShotVersionUpload, {
            shotId: 10,
            onUploaded: (version: VersionOut) => received.push(version),
          }),
      })
  },
})

function chooseFile(wrapper: ReturnType<typeof mount>, file: File) {
  const input = wrapper.find('input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  return input.trigger('change')
}

describe('ShotVersionUpload', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    received.length = 0
    vi.mocked(versionsApi.listVersions).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    })
  })

  it('uploads a chosen file for the shot and reports the created version', async () => {
    vi.mocked(versionsApi.uploadVersion).mockResolvedValue(created)
    const wrapper = mount(Host)
    const file = new File(['x'], 'PRJ_0010_v02.mp4', { type: 'video/mp4' })

    await chooseFile(wrapper, file)
    await flushPromises()

    expect(versionsApi.uploadVersion).toHaveBeenCalledWith(10, file, expect.any(Function))
    expect(received).toEqual([created])
  })

  it('refuses a file with an unsupported extension without calling the API', async () => {
    const wrapper = mount(Host)

    await chooseFile(wrapper, new File(['x'], 'notes.txt', { type: 'text/plain' }))
    await flushPromises()

    expect(versionsApi.uploadVersion).not.toHaveBeenCalled()
    expect(received).toEqual([])
  })

  it('reports nothing when the upload fails', async () => {
    vi.mocked(versionsApi.uploadVersion).mockRejectedValue(new Error('boom'))
    const wrapper = mount(Host)

    await chooseFile(wrapper, new File(['x'], 'PRJ_0010_v02.mp4', { type: 'video/mp4' }))
    await flushPromises()

    expect(received).toEqual([])
    expect(useVersionsStore().uploadState).toBe('idle')
  })

  it('shows the progress while uploading and the processing note after the last byte', async () => {
    let finish: (version: VersionOut) => void = () => {}
    vi.mocked(versionsApi.uploadVersion).mockImplementation(
      (_id, _file, onProgress) =>
        new Promise((resolve) => {
          onProgress?.(100, 100)
          finish = resolve
        }),
    )
    const wrapper = mount(Host)

    await chooseFile(wrapper, new File(['x'], 'PRJ_0010_v02.mp4', { type: 'video/mp4' }))
    await flushPromises()
    expect(wrapper.text()).toContain('идёт обработка')

    finish(created)
    await flushPromises()
    expect(wrapper.text()).not.toContain('идёт обработка')
  })
})
