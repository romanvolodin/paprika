import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import ShotImportPreview from '@/components/shots/ShotImportPreview.vue'
import { useShotImportStore } from '@/stores/shotImport'
import * as projectsApi from '@/api/projects'
import * as shotsApi from '@/api/shots'
import * as tasksApi from '@/api/tasks'
import { readSpreadsheet } from '@/utils/spreadsheet'
import type { CompanyOut, ProjectOut } from '@/types/api'

vi.mock('@/api/projects')
vi.mock('@/api/shots')
vi.mock('@/api/tasks')
vi.mock('@/utils/spreadsheet', () => ({ readSpreadsheet: vi.fn() }))

const company = { id: 7, slug: 'acme' } as CompanyOut
const project = { id: 1, company_id: 7, code: 'PRJ' } as ProjectOut

const Host = defineComponent({
  emits: ['submit'],
  setup(_, { emit }) {
    return () =>
      h(NConfigProvider, null, {
        default: () =>
          h(NMessageProvider, null, {
            default: () => h(ShotImportPreview, { onSubmit: () => emit('submit') }),
          }),
      })
  },
})

async function mountPreview() {
  const store = useShotImportStore()
  await store.open(company, 'PRJ')
  await store.loadFile(new File([''], 'VFX-list.xlsx'))
  const wrapper = mount(Host, { attachTo: document.body })
  await flushPromises()
  return { store, wrapper }
}

function button(wrapper: ReturnType<typeof mount>, text: string) {
  const found = wrapper.findAll('button').find((candidate) => candidate.text().includes(text))
  if (!found) throw new Error(`No button "${text}"`)
  return found
}

describe('ShotImportPreview', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      },
    )
    vi.mocked(projectsApi.listProjects).mockResolvedValue({
      items: [project],
      total: 1,
      page: 1,
      page_size: 1,
    })
    vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({ items: [] })
    vi.mocked(shotsApi.listShotGroups).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
    })
    vi.mocked(shotsApi.listShots).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
    })
    vi.mocked(tasksApi.listTaskTypes).mockResolvedValue({ items: [] })
    vi.mocked(readSpreadsheet).mockResolvedValue([
      {
        name: 'Лист1',
        columnCount: 2,
        rows: [
          { sheetRow: 2, cells: ['A', 'task one'] },
          { sheetRow: 3, cells: ['B', 'task two'] },
        ],
      },
    ])
  })

  it('shows the file, one field picker per column and the rows with their sheet numbers', async () => {
    const { wrapper } = await mountPreview()

    expect(wrapper.text()).toContain('VFX-list.xlsx')
    expect(wrapper.findAll('thead .n-select')).toHaveLength(2)
    // Regression: inside naive-ui's ellipsis box the selects collapsed to
    // zero width, so the person could not pick a field.
    expect(wrapper.find('thead .n-ellipsis').exists()).toBe(false)
    expect(wrapper.text()).toContain('task one')
    const numbers = wrapper.findAll('tbody tr').map((row) => row.findAll('td')[1]?.text())
    expect(numbers).toEqual(['2', '3'])
  })

  it('makes the name cells editable inputs, outside any ellipsis box', async () => {
    const { store, wrapper } = await mountPreview()
    store.setField(0, 'name')
    await flushPromises()

    expect(wrapper.findAll('tbody tr input[type="text"]')).toHaveLength(2)
    expect(wrapper.find('tbody .n-ellipsis').exists()).toBe(false)
  })

  it('keeps "Создать кадры" disabled until a name column is chosen, and says why', async () => {
    const { store, wrapper } = await mountPreview()

    expect(button(wrapper, 'Создать кадры').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('«Имя кадра»')

    store.setField(0, 'name')
    await flushPromises()

    expect(button(wrapper, 'Создать кадры').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).toContain('Будет создано кадров: 2')
  })

  it('skips the selected rows', async () => {
    const { store, wrapper } = await mountPreview()
    store.setField(0, 'name')
    await flushPromises()

    await wrapper.find('tbody tr .n-checkbox').trigger('click')
    expect(wrapper.text()).toContain('Выделено: 1')
    await button(wrapper, 'Пропустить').trigger('click')
    await flushPromises()

    expect(store.rows[0]!.skipped).toBe(true)
    expect(wrapper.text()).toContain('Будет создано кадров: 1')
    expect(wrapper.text()).toContain('пропущено: 1')
  })

  it('shows the problems of a row and blocks the import', async () => {
    vi.mocked(shotsApi.listShots).mockResolvedValue({
      items: [{ id: 1, name: 'A' } as never],
      total: 1,
      page: 1,
      page_size: 100,
    })
    const { store, wrapper } = await mountPreview()
    store.setField(0, 'name')
    await flushPromises()

    expect(wrapper.text()).toContain('Кадр с таким именем уже есть в проекте.')
    expect(button(wrapper, 'Создать кадры').attributes('disabled')).toBeDefined()
  })

  it('selects the rows with problems, so they can be skipped at once', async () => {
    vi.mocked(readSpreadsheet).mockResolvedValue([
      {
        name: 'Лист1',
        columnCount: 2,
        rows: [
          { sheetRow: 1, cells: ['', '01 СЕРИЯ'] },
          { sheetRow: 2, cells: ['A', 'task one'] },
          { sheetRow: 3, cells: ['', '?'] },
        ],
      },
    ])
    const { store, wrapper } = await mountPreview()
    store.setField(0, 'name')
    await flushPromises()

    await button(wrapper, 'Выделить строки с проблемами').trigger('click')
    await button(wrapper, 'Пропустить').trigger('click')
    await flushPromises()

    expect(store.rows.map((row) => row.skipped)).toEqual([true, false, true])
    expect(store.canSubmit).toBe(true)
  })

  it('tells the page to submit', async () => {
    const { store, wrapper } = await mountPreview()
    store.setField(0, 'name')
    await flushPromises()

    await button(wrapper, 'Создать кадры').trigger('click')

    expect(wrapper.emitted('submit')).toHaveLength(1)
  })
})
