import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import ShotVersionsSection from '@/components/shots/ShotVersionsSection.vue'
import { useVersionsStore } from '@/stores/versions'
import * as versionsApi from '@/api/versions'
import type { VersionOut } from '@/types/api'

vi.mock('@/api/versions')

function buildVersion(shotId: number): VersionOut {
  return {
    id: shotId * 10,
    project_id: 1,
    shot_id: shotId,
    name: `PRJ_${shotId}_v01`,
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
}

// The section needs naive-ui's message and dialog providers.
const Host = defineComponent({
  props: {
    shotId: { type: Number, required: true },
    canWrite: { type: Boolean, default: true },
  },
  setup(props) {
    return () =>
      h(NMessageProvider, null, {
        default: () =>
          h(NDialogProvider, null, {
            default: () =>
              h(ShotVersionsSection, { shotId: props.shotId, canWrite: props.canWrite }),
          }),
      })
  },
})

function chooseFile(wrapper: ReturnType<typeof mount>, file: File) {
  const input = wrapper.find('input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  return input.trigger('change')
}

describe('ShotVersionsSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(versionsApi.listVersions).mockImplementation(async (shotId) => ({
      items: [buildVersion(shotId)],
      total: 1,
      page: 1,
      page_size: 20,
    }))
  })

  it('loads the versions of the given shot', async () => {
    mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    expect(versionsApi.listVersions).toHaveBeenCalledWith(10, { page: 1, page_size: 20 })
    expect(useVersionsStore().items[0]?.shot_id).toBe(10)
  })

  // Moving from one shot page to another reuses the section with a new
  // shotId; the versions must follow it.
  it('reloads the versions when the shot changes', async () => {
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    await wrapper.setProps({ shotId: 11 })
    await flushPromises()

    expect(versionsApi.listVersions).toHaveBeenLastCalledWith(11, { page: 1, page_size: 20 })
    expect(useVersionsStore().items.map((version) => version.shot_id)).toEqual([11])
  })

  it('shows the upload and delete controls to members who can write', async () => {
    const wrapper = mount(Host, { props: { shotId: 10, canWrite: true } })
    await flushPromises()

    expect(wrapper.text()).toContain('Загрузить версию')
    expect(wrapper.text()).toContain('Удалить')
  })

  it('hides the upload and delete controls from read-only members', async () => {
    const wrapper = mount(Host, { props: { shotId: 10, canWrite: false } })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Загрузить версию')
    expect(wrapper.text()).not.toContain('Удалить')
    expect(wrapper.text()).toContain('PRJ_10_v01')
  })

  it('uploads a chosen file for the current shot', async () => {
    vi.mocked(versionsApi.uploadVersion).mockResolvedValue(buildVersion(10))
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()
    const file = new File(['x'], 'PRJ_10_v02.mp4', { type: 'video/mp4' })

    await chooseFile(wrapper, file)
    await flushPromises()

    expect(versionsApi.uploadVersion).toHaveBeenCalledWith(10, file, expect.any(Function))
  })

  it('refuses a file with an unsupported extension without calling the API', async () => {
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    await chooseFile(wrapper, new File(['x'], 'notes.txt', { type: 'text/plain' }))
    await flushPromises()

    expect(versionsApi.uploadVersion).not.toHaveBeenCalled()
  })
})
