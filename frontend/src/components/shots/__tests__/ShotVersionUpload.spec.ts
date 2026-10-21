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

function submitButton(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('button').find((button) => button.text() === 'Отправить версию')!
}

const video = new File(['x'], 'PRJ_0010_v02.mp4', { type: 'video/mp4' })
const image = new File(['x'], 'frame.PNG', { type: 'image/png' })

describe('ShotVersionUpload', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    received.length = 0
    URL.createObjectURL = vi.fn(() => 'blob:preview')
    URL.revokeObjectURL = vi.fn()
    vi.mocked(versionsApi.listVersions).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    })
  })

  it('asks for a file first, with nothing to send yet', () => {
    const wrapper = mount(Host)

    expect(wrapper.find('[data-test="drop-zone"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="preview"]').exists()).toBe(false)
    expect(submitButton(wrapper).attributes('disabled')).toBeDefined()
  })

  it('shows a live preview of a chosen video without uploading it', async () => {
    const wrapper = mount(Host)

    await chooseFile(wrapper, video)

    expect(wrapper.find('[data-test="drop-zone"]').exists()).toBe(false)
    expect(wrapper.find('video').attributes('src')).toBe('blob:preview')
    expect(wrapper.find('video').attributes('controls')).toBeDefined()
    expect(wrapper.text()).toContain('PRJ_0010_v02.mp4')
    expect(versionsApi.uploadVersion).not.toHaveBeenCalled()
    expect(submitButton(wrapper).attributes('disabled')).toBeUndefined()
  })

  it('shows a chosen image as a picture, whatever the case of its extension', async () => {
    const wrapper = mount(Host)

    await chooseFile(wrapper, image)

    expect(wrapper.find('video').exists()).toBe(false)
    expect(wrapper.find('img').attributes('src')).toBe('blob:preview')
  })

  it('takes a file dropped on the zone', async () => {
    const wrapper = mount(Host)

    await wrapper.find('[data-test="drop-zone"]').trigger('drop', {
      dataTransfer: { files: [video] },
    })

    expect(wrapper.find('video').exists()).toBe(true)
  })

  it('takes the first of several dropped files', async () => {
    const wrapper = mount(Host)

    await wrapper.find('[data-test="drop-zone"]').trigger('drop', {
      dataTransfer: { files: [image, video] },
    })

    expect(wrapper.find('img').exists()).toBe(true)
    expect(wrapper.find('video').exists()).toBe(false)
  })

  it('refuses a file with an unsupported extension and keeps asking for one', async () => {
    const wrapper = mount(Host)

    await chooseFile(wrapper, new File(['x'], 'notes.txt', { type: 'text/plain' }))

    expect(wrapper.find('[data-test="drop-zone"]').exists()).toBe(true)
    expect(URL.createObjectURL).not.toHaveBeenCalled()
  })

  it('goes back to the choice on a reset and frees the preview', async () => {
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)

    await wrapper.find('button[aria-label="Сбросить файл"]').trigger('click')

    expect(wrapper.find('[data-test="drop-zone"]').exists()).toBe(true)
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview')
  })

  it('frees the preview of the earlier file when another one is chosen', async () => {
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)
    await wrapper.find('button[aria-label="Сбросить файл"]').trigger('click')

    await chooseFile(wrapper, image)

    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(1)
    expect(URL.createObjectURL).toHaveBeenCalledTimes(2)
  })

  it('frees the preview when the page is left', async () => {
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)

    wrapper.unmount()

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview')
  })

  it('uploads the chosen file for the shot on send and reports the created version', async () => {
    vi.mocked(versionsApi.uploadVersion).mockResolvedValue(created)
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)

    await submitButton(wrapper).trigger('click')
    await flushPromises()

    expect(versionsApi.uploadVersion).toHaveBeenCalledWith(10, video, expect.any(Function))
    expect(received).toEqual([created])
  })

  it('keeps the chosen file when the upload fails, so it can be sent again', async () => {
    vi.mocked(versionsApi.uploadVersion).mockRejectedValue(new Error('boom'))
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)

    await submitButton(wrapper).trigger('click')
    await flushPromises()

    expect(received).toEqual([])
    expect(useVersionsStore().uploadState).toBe('idle')
    expect(wrapper.find('video').exists()).toBe(true)
    expect(submitButton(wrapper).attributes('disabled')).toBeUndefined()
  })

  it('locks the reset and the send button while uploading and shows the processing note', async () => {
    let finish: (version: VersionOut) => void = () => {}
    vi.mocked(versionsApi.uploadVersion).mockImplementation(
      (_id, _file, onProgress) =>
        new Promise((resolve) => {
          onProgress?.(100, 100)
          finish = resolve
        }),
    )
    const wrapper = mount(Host)
    await chooseFile(wrapper, video)

    await submitButton(wrapper).trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('идёт обработка')
    expect(submitButton(wrapper).attributes('disabled')).toBeDefined()
    expect(wrapper.find('button[aria-label="Сбросить файл"]').attributes('disabled')).toBeDefined()

    finish(created)
    await flushPromises()
    expect(wrapper.text()).not.toContain('идёт обработка')
  })
})
