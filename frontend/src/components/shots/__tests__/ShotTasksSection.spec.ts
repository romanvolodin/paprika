import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import ShotTasksSection from '@/components/shots/ShotTasksSection.vue'
import { useAuthStore } from '@/stores/auth'
import { useShotTasksStore } from '@/stores/shotTasks'
import * as tasksApi from '@/api/tasks'
import type { ProjectMemberOut, ShotTaskOut } from '@/types/api'

vi.mock('@/api/tasks')

function buildShotTask(shotId: number, assigneeId: number | null = null): ShotTaskOut {
  return {
    id: shotId * 10,
    shot_id: shotId,
    task: {
      id: 100,
      project_id: 1,
      code: `PRJ${shotId}`,
      name: `Task of shot ${shotId}`,
      description: '',
      type_id: 1,
      shot_ids: [shotId],
      created_by: null,
      updated_by: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
    status_id: 2,
    assignee:
      assigneeId === null
        ? null
        : ({ id: assigneeId, first_name: 'A', last_name: 'One' } as ShotTaskOut['assignee']),
    estimated_hours: 8,
    actual_hours: null,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

const members: ProjectMemberOut[] = []

// The section needs naive-ui's message and dialog providers.
const Host = defineComponent({
  props: {
    shotId: { type: Number, required: true },
    canWrite: { type: Boolean, default: true },
    // Only the right to change the status of one's own tasks.
    onlyOwnStatus: { type: Boolean, default: false },
  },
  setup(props) {
    return () =>
      h(NMessageProvider, null, {
        default: () =>
          h(NDialogProvider, null, {
            default: () =>
              h(ShotTasksSection, {
                shotId: props.shotId,
                projectId: 1,
                companyId: 7,
                members,
                canCreate: props.canWrite && !props.onlyOwnStatus,
                canEdit: props.canWrite && !props.onlyOwnStatus,
                canDelete: props.canWrite && !props.onlyOwnStatus,
                canUpdateOwn: props.canWrite || props.onlyOwnStatus,
              }),
          }),
      })
  },
})

describe('ShotTasksSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(tasksApi.listShotTasks).mockImplementation(async (shotId) => ({
      items: [buildShotTask(shotId)],
    }))
    vi.mocked(tasksApi.listTaskTypes).mockResolvedValue({ items: [] })
    vi.mocked(tasksApi.listTaskStatuses).mockResolvedValue({ items: [] })
  })

  it('loads and lists the tasks of the given shot', async () => {
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    expect(tasksApi.listShotTasks).toHaveBeenCalledWith(10)
    expect(wrapper.text()).toContain('PRJ10')
    expect(wrapper.text()).toContain('Task of shot 10')
  })

  // Moving from one shot page to another reuses the section with a new
  // shotId; the tasks must follow it.
  it('reloads the tasks when the shot changes', async () => {
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    await wrapper.setProps({ shotId: 11 })
    await flushPromises()

    expect(tasksApi.listShotTasks).toHaveBeenLastCalledWith(11)
    expect(useShotTasksStore().items.map((item) => item.shot_id)).toEqual([11])
  })

  it('shows the add, hours and remove controls to members who can write', async () => {
    const wrapper = mount(Host, { props: { shotId: 10, canWrite: true } })
    await flushPromises()

    expect(wrapper.text()).toContain('Добавить задачу')
    expect(wrapper.text()).toContain('Часы')
    expect(wrapper.text()).toContain('Снять')
  })

  it('hides the controls from read-only members but still lists the tasks', async () => {
    const wrapper = mount(Host, { props: { shotId: 10, canWrite: false } })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Добавить задачу')
    expect(wrapper.text()).not.toContain('Снять')
    expect(wrapper.text()).toContain('PRJ10')
  })

  describe('when the user may only change the status of their own tasks', () => {
    beforeEach(() => {
      useAuthStore().currentUser = {
        id: 5,
        email: 'me@paprika.dev',
        first_name: 'Me',
        last_name: 'Myself',
        avatar: null,
        is_active: true,
        date_joined: '2026-01-01T00:00:00Z',
      }
    })

    it('offers the status of a task assigned to them, but nothing else', async () => {
      vi.mocked(tasksApi.listShotTasks).mockResolvedValue({ items: [buildShotTask(10, 5)] })
      const wrapper = mount(Host, { props: { shotId: 10, onlyOwnStatus: true } })
      await flushPromises()

      expect(wrapper.findAll('.n-select')).toHaveLength(1)
      const buttons = wrapper.findAll('button').map((button) => button.text())
      expect(buttons).not.toContain('Добавить задачу')
      expect(buttons).not.toContain('Часы')
      expect(buttons).not.toContain('Снять')
    })

    it("shows the status of someone else's task as plain text", async () => {
      vi.mocked(tasksApi.listShotTasks).mockResolvedValue({ items: [buildShotTask(10, 6)] })
      const wrapper = mount(Host, { props: { shotId: 10, onlyOwnStatus: true } })
      await flushPromises()

      expect(wrapper.findAll('.n-select')).toHaveLength(0)
    })
  })
})
