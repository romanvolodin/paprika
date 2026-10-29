import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import { createMemoryHistory, createRouter } from 'vue-router'
import ShotVersionsSection from '@/components/shots/ShotVersionsSection.vue'
import { useAuthStore } from '@/stores/auth'
import { useVersionsStore } from '@/stores/versions'
import * as versionsApi from '@/api/versions'
import type { VersionOut } from '@/types/api'

vi.mock('@/api/versions')

function buildVersion(shotId: number, uploaderId: number | null = null): VersionOut {
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
    created_by:
      uploaderId === null
        ? null
        : ({ id: uploaderId, first_name: 'A', last_name: 'One' } as VersionOut['created_by']),
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
    // Only the right to delete one's own versions.
    onlyDeleteOwn: { type: Boolean, default: false },
  },
  setup(props) {
    return () =>
      h(NMessageProvider, null, {
        default: () =>
          h(NDialogProvider, null, {
            default: () =>
              h(ShotVersionsSection, {
                shotId: props.shotId,
                canUpload: props.canWrite,
                canDelete: props.canWrite && !props.onlyDeleteOwn,
                canDeleteOwn: props.canWrite || props.onlyDeleteOwn,
                uploadTo: { name: 'shot-upload' },
              }),
          }),
      })
  },
})

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { render: () => null } },
    { path: '/upload', name: 'shot-upload', component: { render: () => null } },
  ],
})

function mountSection(props: { shotId: number; canWrite?: boolean; onlyDeleteOwn?: boolean }) {
  return mount(Host, { props, global: { plugins: [router] } })
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
    mountSection({ shotId: 10 })
    await flushPromises()

    expect(versionsApi.listVersions).toHaveBeenCalledWith(10, { page: 1, page_size: 20 })
    expect(useVersionsStore().items[0]?.shot_id).toBe(10)
  })

  // Moving from one shot page to another reuses the section with a new
  // shotId; the versions must follow it.
  it('reloads the versions when the shot changes', async () => {
    const wrapper = mountSection({ shotId: 10 })
    await flushPromises()

    await wrapper.setProps({ shotId: 11 })
    await flushPromises()

    expect(versionsApi.listVersions).toHaveBeenLastCalledWith(11, { page: 1, page_size: 20 })
    expect(useVersionsStore().items.map((version) => version.shot_id)).toEqual([11])
  })

  it('shows the upload and delete controls to members who can write', async () => {
    const wrapper = mountSection({ shotId: 10, canWrite: true })
    await flushPromises()

    expect(wrapper.text()).toContain('Загрузить версию')
    expect(wrapper.text()).toContain('Удалить')
  })

  it('hides the upload and delete controls from read-only members', async () => {
    const wrapper = mountSection({ shotId: 10, canWrite: false })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Загрузить версию')
    expect(wrapper.text()).not.toContain('Удалить')
    expect(wrapper.text()).toContain('PRJ_10_v01')
  })

  describe('when the user may only delete their own versions', () => {
    beforeEach(() => {
      useAuthStore().currentUser = {
        id: 5,
        email: 'me@paprika.dev',
        first_name: 'Me',
        last_name: 'Myself',
        avatar: null,
        is_active: true,
        date_joined: '2026-01-01T00:00:00Z',
        is_superuser: false,
        must_change_password: false,
      }
    })

    it('offers the delete button for a version they uploaded', async () => {
      vi.mocked(versionsApi.listVersions).mockResolvedValue({
        items: [buildVersion(10, 5)],
        total: 1,
        page: 1,
        page_size: 20,
      })
      const wrapper = mountSection({ shotId: 10, canWrite: false, onlyDeleteOwn: true })
      await flushPromises()

      expect(wrapper.findAll('button').map((button) => button.text())).toContain('Удалить')
    })

    it("hides it for someone else's version", async () => {
      vi.mocked(versionsApi.listVersions).mockResolvedValue({
        items: [buildVersion(10, 6)],
        total: 1,
        page: 1,
        page_size: 20,
      })
      const wrapper = mountSection({ shotId: 10, canWrite: false, onlyDeleteOwn: true })
      await flushPromises()

      expect(wrapper.findAll('button').map((button) => button.text())).not.toContain('Удалить')
    })
  })

  it('leads the upload button to the upload page', async () => {
    const wrapper = mountSection({ shotId: 10 })
    await flushPromises()

    const button = wrapper.find('a.shot-versions__upload')
    expect(button.text()).toBe('Загрузить версию')
    expect(button.attributes('href')).toBe('/upload')
  })
})
