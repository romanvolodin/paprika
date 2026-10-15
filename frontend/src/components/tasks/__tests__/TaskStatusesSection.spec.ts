import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { AxiosError } from 'axios'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import TaskStatusesSection from '@/components/tasks/TaskStatusesSection.vue'
import { useTaskStatusesStore } from '@/stores/taskStatuses'
import * as tasksApi from '@/api/tasks'
import type { TaskStatusOut } from '@/types/api'

vi.mock('@/api/tasks')

function buildStatus(overrides: Partial<TaskStatusOut> = {}): TaskStatusOut {
  return {
    id: 1,
    company_id: 7,
    name: 'In progress',
    color: '#3366ff',
    order: 2,
    is_default: false,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const Host = defineComponent({
  props: {
    companyId: { type: Number, required: true },
    canEdit: { type: Boolean, default: true },
  },
  setup(props) {
    return () =>
      h(NMessageProvider, null, {
        default: () =>
          h(NDialogProvider, null, {
            default: () =>
              h(TaskStatusesSection, { companyId: props.companyId, canEdit: props.canEdit }),
          }),
      })
  },
})

function conflict(message: string) {
  return new AxiosError('Conflict', 'ERR_BAD_REQUEST', undefined, undefined, {
    status: 409,
    data: { detail: [{ msg: message }] },
  } as never)
}

function bodyButton(text: string): HTMLElement | undefined {
  return [...document.body.querySelectorAll<HTMLElement>('button')].find((button) =>
    button.textContent?.includes(text),
  )
}

// The confirmation dialog, as opposed to the same-named button in a table row.
function dialogButton(text: string): HTMLElement | undefined {
  return [...document.body.querySelectorAll<HTMLElement>('.n-dialog button')].find((button) =>
    button.textContent?.includes(text),
  )
}

function fill(input: HTMLInputElement, value: string) {
  input.value = value
  input.dispatchEvent(new Event('input', { bubbles: true }))
}

let wrapper: VueWrapper | null = null

function mountSection(props: { companyId: number; canEdit?: boolean }) {
  wrapper = mount(Host, { props, attachTo: document.body })
  return wrapper
}

describe('TaskStatusesSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(tasksApi.listTaskStatuses).mockImplementation(async (companyId) => ({
      items: [
        buildStatus({ company_id: companyId, name: `Status of company ${companyId}` }),
        buildStatus({
          id: 2,
          company_id: companyId,
          name: 'Not started',
          order: null,
          is_default: true,
        }),
      ],
    }))
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    document.body.innerHTML = ''
  })

  it('lists the statuses with their order and the default mark', async () => {
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    const rows = view.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0]?.text()).toContain('Status of company 7')
    expect(rows[0]?.text()).toContain('2')
    expect(rows[1]?.text()).toContain('—')
    expect(rows[1]?.text()).toContain('Да')
  })

  it('reloads the statuses when the company changes', async () => {
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    await view.setProps({ companyId: 8 })
    await flushPromises()

    expect(tasksApi.listTaskStatuses).toHaveBeenLastCalledWith(8)
    expect(useTaskStatusesStore().items.map((status) => status.company_id)).toEqual([8, 8])
  })

  it('shows the statuses but no controls to members who cannot edit', async () => {
    const view = mountSection({ companyId: 7, canEdit: false })
    await flushPromises()

    expect(view.text()).toContain('Status of company 7')
    expect(view.text()).not.toContain('Добавить статус')
    expect(view.text()).not.toContain('Изменить')
    expect(view.text()).not.toContain('Удалить')
  })

  it('creates a status without an order as outside the main workflow', async () => {
    vi.mocked(tasksApi.createTaskStatus).mockResolvedValue(buildStatus({ id: 3 }))
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Добавить статус')))?.trigger(
      'click',
    )
    await flushPromises()
    fill(document.body.querySelector<HTMLInputElement>('.n-modal input[type="text"]')!, ' On hold ')
    await flushPromises()
    bodyButton('Сохранить')?.click()
    await flushPromises()

    expect(tasksApi.createTaskStatus).toHaveBeenCalledWith(7, {
      name: 'On hold',
      color: '#888888',
      order: null,
      is_default: false,
    })
  })

  it('does not send a status without a name', async () => {
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Добавить статус')))?.trigger(
      'click',
    )
    await flushPromises()
    bodyButton('Сохранить')?.click()
    await flushPromises()

    expect(tasksApi.createTaskStatus).not.toHaveBeenCalled()
  })

  it('explains a duplicate status name', async () => {
    vi.mocked(tasksApi.createTaskStatus).mockRejectedValue(
      conflict('A task status with this name already exists in this company.'),
    )
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Добавить статус')))?.trigger(
      'click',
    )
    await flushPromises()
    fill(document.body.querySelector<HTMLInputElement>('.n-modal input[type="text"]')!, 'Done')
    await flushPromises()
    bodyButton('Сохранить')?.click()
    await flushPromises()

    expect(document.body.textContent).toContain('Статус с таким названием уже есть в компании.')
  })

  it('opens a status for editing with its current values', async () => {
    vi.mocked(tasksApi.updateTaskStatus).mockResolvedValue(buildStatus())
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Изменить')))?.trigger('click')
    await flushPromises()
    const nameInput = document.body.querySelector<HTMLInputElement>('.n-modal input[type="text"]')!
    expect(nameInput.value).toBe('Status of company 7')
    fill(nameInput, 'Renamed')
    await flushPromises()
    bodyButton('Сохранить')?.click()
    await flushPromises()

    expect(tasksApi.updateTaskStatus).toHaveBeenCalledWith(1, {
      name: 'Renamed',
      color: '#3366ff',
      order: 2,
      is_default: false,
    })
  })

  it('explains that a status used by shot tasks cannot be deleted', async () => {
    vi.mocked(tasksApi.deleteTaskStatus).mockRejectedValue(
      conflict('Cannot delete this status while shot tasks still use it.'),
    )
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Удалить')))?.trigger('click')
    await flushPromises()
    dialogButton('Удалить')?.click()
    await flushPromises()

    expect(tasksApi.deleteTaskStatus).toHaveBeenCalledWith(1)
    expect(document.body.textContent).toContain(
      'Статус используется задачами на кадрах, удалить его нельзя.',
    )
  })
})
