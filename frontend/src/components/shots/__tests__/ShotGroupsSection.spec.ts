import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import ShotGroupsSection from '@/components/shots/ShotGroupsSection.vue'
import { useShotGroupsStore } from '@/stores/shotGroups'
import * as shotsApi from '@/api/shots'
import type { ShotGroupOut } from '@/types/api'

vi.mock('@/api/shots')

function buildGroup(projectId: number, name: string): ShotGroupOut {
  return {
    id: projectId * 10,
    project_id: projectId,
    name,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

// The section needs naive-ui's message and dialog providers.
const Host = defineComponent({
  props: { projectId: { type: Number, required: true } },
  setup(props) {
    return () =>
      h(NMessageProvider, null, {
        default: () =>
          h(NDialogProvider, null, {
            default: () => h(ShotGroupsSection, { projectId: props.projectId, canWrite: false }),
          }),
      })
  },
})

describe('ShotGroupsSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(shotsApi.listShotGroups).mockImplementation(async (projectId) => ({
      items: [buildGroup(projectId, `Group of project ${projectId}`)],
      total: 1,
      page: 1,
      page_size: 100,
    }))
  })

  it('loads the groups of the given project', async () => {
    mount(Host, { props: { projectId: 1 } })
    await flushPromises()

    expect(shotsApi.listShotGroups).toHaveBeenCalledWith(1, { page_size: 100 })
    expect(useShotGroupsStore().items[0]?.project_id).toBe(1)
  })

  // Regression: moving from one project page to another reuses the
  // section with a new projectId; the groups must follow it.
  it('reloads the groups when the project changes', async () => {
    const wrapper = mount(Host, { props: { projectId: 1 } })
    await flushPromises()

    await wrapper.setProps({ projectId: 2 })
    await flushPromises()

    expect(shotsApi.listShotGroups).toHaveBeenLastCalledWith(2, { page_size: 100 })
    expect(useShotGroupsStore().items.map((group) => group.project_id)).toEqual([2])
  })
})
