import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { NButton, NConfigProvider, NInput, NSelect } from 'naive-ui'
import ShotImportAssignModal from '@/components/shots/ShotImportAssignModal.vue'
import * as tasksApi from '@/api/tasks'
import type { NewImportTask } from '@/utils/shotImport'
import type { ShotGroupOut, TaskOut, TaskTypeOut } from '@/types/api'

vi.mock('@/api/tasks')

const pendingTask: NewImportTask = {
  kind: 'new',
  name: 'Вставка в монитор',
  typeId: 3,
  typeName: 'Композ',
}

function mountModal(props: { mode: 'group' | 'task'; pendingGroups?: string[] }) {
  const Host = defineComponent({
    setup() {
      return () =>
        h(NConfigProvider, null, {
          default: () =>
            h(ShotImportAssignModal, {
              show: true,
              mode: props.mode,
              rowCount: 2,
              projectId: 1,
              groups: [{ id: 1, name: '01 СЕРИЯ' } as ShotGroupOut],
              taskTypes: [{ id: 3, name: 'Композ', abbreviation: 'CMP' } as TaskTypeOut],
              pendingGroups: props.pendingGroups ?? [],
              pendingTasks: [pendingTask],
              'onAdd-group': (name: string) => added.group.push(name),
              'onAdd-task': (task: unknown) => added.task.push(task),
            }),
        })
    },
  })
  const added = { group: [] as string[], task: [] as unknown[] }
  const wrapper = mount(Host, { attachTo: document.body })
  return { wrapper, added }
}

function confirm(wrapper: ReturnType<typeof mount>) {
  const found = wrapper.findAllComponents(NButton).find((button) => button.text() === 'Добавить')
  if (!found) throw new Error('No confirm button')
  return found.trigger('click')
}

describe('ShotImportAssignModal', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(tasksApi.listTasks).mockResolvedValue({
      items: [{ id: 5, name: 'Клинап', code: 'CLN0001' } as TaskOut],
      total: 1,
      page: 1,
      page_size: 20,
    })
  })

  it('lists the project groups and the new groups given to other rows', () => {
    const { wrapper } = mountModal({ mode: 'group', pendingGroups: ['02 СЕРИЯ'] })

    const options = wrapper.findComponent(NSelect).props('options')

    expect(options).toEqual([
      { label: '01 СЕРИЯ', value: '01 СЕРИЯ' },
      { label: '02 СЕРИЯ (новая)', value: '02 СЕРИЯ' },
    ])
  })

  it('gives a pending group to the rows by its name', async () => {
    const { wrapper, added } = mountModal({ mode: 'group', pendingGroups: ['02 СЕРИЯ'] })

    wrapper.findComponent(NSelect).vm.$emit('update:value', '02 СЕРИЯ')
    await flushPromises()
    await confirm(wrapper)

    expect(added.group).toEqual(['02 СЕРИЯ'])
  })

  it('lists the new tasks given to other rows among the tasks to pick', () => {
    const { wrapper } = mountModal({ mode: 'task' })

    expect(wrapper.findComponent(NSelect).props('options')).toEqual([
      { label: '+ Вставка в монитор (Композ) · новая', value: 'new:3:Вставка в монитор' },
    ])
  })

  it('gives a pending new task to the rows as it was defined', async () => {
    const { wrapper, added } = mountModal({ mode: 'task' })

    wrapper.findComponent(NSelect).vm.$emit('update:value', 'new:3:Вставка в монитор')
    await flushPromises()
    await confirm(wrapper)

    expect(added.task).toEqual([pendingTask])
  })

  it('narrows the pending tasks by what is typed', async () => {
    const { wrapper } = mountModal({ mode: 'task' })

    wrapper.findComponent(NSelect).vm.$emit('search', 'клин')
    await flushPromises()

    expect(wrapper.findComponent(NSelect).props('options')).toEqual([])
  })

  it('still gives an existing task by its id', async () => {
    vi.useFakeTimers()
    const { wrapper, added } = mountModal({ mode: 'task' })
    const select = wrapper.findComponent(NSelect)

    select.vm.$emit('search', 'клин')
    await vi.advanceTimersByTimeAsync(400)
    vi.useRealTimers()
    await flushPromises()
    select.vm.$emit('update:value', 5)
    await flushPromises()
    await confirm(wrapper)

    expect(added.task).toEqual([{ kind: 'existing', taskId: 5, name: 'Клинап', code: 'CLN0001' }])
  })

  it('makes a brand new task from a name and a type', async () => {
    const { wrapper, added } = mountModal({ mode: 'task' })
    wrapper
      .findAllComponents(NButton)
      .find((button) => button.text().startsWith('Создать новую задачу'))!
      .trigger('click')
    await flushPromises()

    wrapper.findComponent(NInput).vm.$emit('update:value', 'Клинап титров')
    wrapper.findAllComponents(NSelect)[0]!.vm.$emit('update:value', 3)
    await flushPromises()
    await confirm(wrapper)

    expect(added.task).toEqual([
      { kind: 'new', name: 'Клинап титров', typeId: 3, typeName: 'Композ' },
    ])
  })
})
