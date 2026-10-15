import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { AxiosError } from 'axios'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import TaskTypesSection from '@/components/tasks/TaskTypesSection.vue'
import { useTaskTypesStore } from '@/stores/taskTypes'
import * as tasksApi from '@/api/tasks'
import type { TaskTypeOut } from '@/types/api'

vi.mock('@/api/tasks')

function buildType(overrides: Partial<TaskTypeOut> = {}): TaskTypeOut {
  return {
    id: 1,
    company_id: 7,
    name: 'Cleanup',
    abbreviation: 'CLN',
    color: '#3366ff',
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

// The section needs naive-ui's message and dialog providers.
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
              h(TaskTypesSection, { companyId: props.companyId, canEdit: props.canEdit }),
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

// Modals and dialogs are teleported to the body.
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

function modalInputs(): HTMLInputElement[] {
  return [...document.body.querySelectorAll<HTMLInputElement>('.n-modal input[type="text"]')]
}

let wrapper: VueWrapper | null = null

function mountSection(props: { companyId: number; canEdit?: boolean }) {
  wrapper = mount(Host, { props, attachTo: document.body })
  return wrapper
}

describe('TaskTypesSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(tasksApi.listTaskTypes).mockImplementation(async (companyId) => ({
      items: [buildType({ company_id: companyId, name: `Type of company ${companyId}` })],
    }))
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    document.body.innerHTML = ''
  })

  it('lists the task types of the company', async () => {
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    expect(tasksApi.listTaskTypes).toHaveBeenCalledWith(7)
    expect(view.text()).toContain('Type of company 7')
    expect(view.text()).toContain('CLN')
  })

  // Moving from one company page to another reuses the section with a
  // new companyId; the types must follow it.
  it('reloads the types when the company changes', async () => {
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    await view.setProps({ companyId: 8 })
    await flushPromises()

    expect(tasksApi.listTaskTypes).toHaveBeenLastCalledWith(8)
    expect(useTaskTypesStore().items.map((type) => type.company_id)).toEqual([8])
  })

  it('offers add, edit and delete to company admins', async () => {
    const view = mountSection({ companyId: 7, canEdit: true })
    await flushPromises()

    expect(view.text()).toContain('Добавить тип')
    expect(view.text()).toContain('Изменить')
    expect(view.text()).toContain('Удалить')
  })

  it('shows the types but no controls to other members', async () => {
    const view = mountSection({ companyId: 7, canEdit: false })
    await flushPromises()

    expect(view.text()).toContain('Type of company 7')
    expect(view.text()).not.toContain('Добавить тип')
    expect(view.text()).not.toContain('Изменить')
    expect(view.text()).not.toContain('Удалить')
  })

  it('creates a type, writing the abbreviation in capitals', async () => {
    vi.mocked(tasksApi.createTaskType).mockResolvedValue(buildType({ id: 2 }))
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Добавить тип')))?.trigger('click')
    await flushPromises()
    const [nameInput, abbreviationInput] = modalInputs()
    fill(nameInput!, '  Roto  ')
    fill(abbreviationInput!, 'rto')
    await flushPromises()
    bodyButton('Сохранить')?.click()
    await flushPromises()

    expect(tasksApi.createTaskType).toHaveBeenCalledWith(7, {
      name: 'Roto',
      abbreviation: 'RTO',
      color: '#888888',
    })
  })

  it('does not send an abbreviation that breaks the backend rule', async () => {
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Добавить тип')))?.trigger('click')
    await flushPromises()
    const [nameInput, abbreviationInput] = modalInputs()
    fill(nameInput!, 'Roto')
    fill(abbreviationInput!, 'R')
    await flushPromises()
    bodyButton('Сохранить')?.click()
    await flushPromises()

    expect(tasksApi.createTaskType).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain('2–5 заглавных латинских букв или цифр')
  })

  it('does not send a type without a name', async () => {
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Добавить тип')))?.trigger('click')
    await flushPromises()
    fill(modalInputs()[1]!, 'RTO')
    await flushPromises()
    bodyButton('Сохранить')?.click()
    await flushPromises()

    expect(tasksApi.createTaskType).not.toHaveBeenCalled()
  })

  it('tells a duplicate abbreviation from a duplicate name', async () => {
    vi.mocked(tasksApi.createTaskType)
      .mockRejectedValueOnce(
        conflict('A task type with this abbreviation already exists in this company.'),
      )
      .mockRejectedValueOnce(conflict('A task type with this name already exists in this company.'))
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Добавить тип')))?.trigger('click')
    await flushPromises()
    fill(modalInputs()[0]!, 'Roto')
    fill(modalInputs()[1]!, 'RTO')
    await flushPromises()
    bodyButton('Сохранить')?.click()
    await flushPromises()
    expect(document.body.textContent).toContain('Тип с такой аббревиатурой уже есть в компании.')

    bodyButton('Сохранить')?.click()
    await flushPromises()
    expect(document.body.textContent).toContain('Тип с таким названием уже есть в компании.')
  })

  it('opens an existing type for editing with its current values and saves the changes', async () => {
    vi.mocked(tasksApi.updateTaskType).mockResolvedValue(buildType())
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Изменить')))?.trigger('click')
    await flushPromises()
    const [nameInput, abbreviationInput] = modalInputs()
    expect(nameInput?.value).toBe('Type of company 7')
    expect(abbreviationInput?.value).toBe('CLN')
    expect(document.body.textContent).toContain('не меняет коды уже созданных задач')
    fill(nameInput!, 'Renamed')
    await flushPromises()
    bodyButton('Сохранить')?.click()
    await flushPromises()

    expect(tasksApi.updateTaskType).toHaveBeenCalledWith(1, {
      name: 'Renamed',
      abbreviation: 'CLN',
      color: '#3366ff',
    })
  })

  it('explains that a type used by tasks cannot be deleted', async () => {
    vi.mocked(tasksApi.deleteTaskType).mockRejectedValue(
      conflict('Cannot delete this task type while tasks still use it.'),
    )
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Удалить')))?.trigger('click')
    await flushPromises()
    dialogButton('Удалить')?.click()
    await flushPromises()

    expect(tasksApi.deleteTaskType).toHaveBeenCalledWith(1)
    expect(document.body.textContent).toContain('Тип используется задачами, удалить его нельзя.')
  })

  it('deletes an unused type after confirmation', async () => {
    vi.mocked(tasksApi.deleteTaskType).mockResolvedValue(undefined as never)
    const view = mountSection({ companyId: 7 })
    await flushPromises()

    ;(await view.findAll('button').find((b) => b.text().includes('Удалить')))?.trigger('click')
    await flushPromises()
    expect(tasksApi.deleteTaskType).not.toHaveBeenCalled()
    dialogButton('Удалить')?.click()
    await flushPromises()

    expect(tasksApi.deleteTaskType).toHaveBeenCalledWith(1)
    expect(document.body.textContent).toContain('Тип удалён.')
  })
})
