import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { AxiosError } from 'axios'
import { useShotImportStore } from '@/stores/shotImport'
import * as projectsApi from '@/api/projects'
import * as shotImportApi from '@/api/shotImport'
import * as shotsApi from '@/api/shots'
import * as tasksApi from '@/api/tasks'
import { readSpreadsheet } from '@/utils/spreadsheet'
import type { CompanyOut, ProjectOut, ShotOut } from '@/types/api'

vi.mock('@/api/projects')
vi.mock('@/api/shotImport')
vi.mock('@/api/shots')
vi.mock('@/api/tasks')
vi.mock('@/utils/spreadsheet', () => ({ readSpreadsheet: vi.fn() }))

const company = { id: 7, name: 'Acme', slug: 'acme' } as CompanyOut
const project = { id: 1, company_id: 7, code: 'PRJ', name: 'Film' } as ProjectOut

function shot(name: string) {
  return { id: 1, name } as ShotOut
}

function sheet() {
  return {
    name: 'Лист1',
    columnCount: 3,
    rows: [
      { sheetRow: 1, cells: ['шот', 'ТК', 'задача'] },
      { sheetRow: 3, cells: ['A', '00:00:01:05', 'вставка'] },
      { sheetRow: 4, cells: ['B', '', ''] },
    ],
  }
}

async function openedStore() {
  const store = useShotImportStore()
  await store.open(company, 'PRJ')
  return store
}

async function storeWithFile(names: string[] = []) {
  vi.mocked(readSpreadsheet).mockResolvedValue([sheet()])
  vi.mocked(shotsApi.listShots).mockResolvedValue({
    items: names.map(shot),
    total: names.length,
    page: 1,
    page_size: 100,
  })
  const store = await openedStore()
  await store.loadFile(new File([''], 'list.xlsx'))
  return store
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.resetAllMocks()
  vi.mocked(projectsApi.listProjects).mockResolvedValue({
    items: [project],
    total: 1,
    page: 1,
    page_size: 1,
  })
  vi.mocked(projectsApi.listProjectMembers).mockResolvedValue({ items: [] })
  vi.mocked(shotsApi.listShotGroups).mockResolvedValue({
    items: [{ id: 1, name: '01 СЕРИЯ' }],
    total: 1,
    page: 1,
    page_size: 100,
  } as never)
  vi.mocked(tasksApi.listTaskTypes).mockResolvedValue({
    items: [{ id: 3, name: 'Композ' }],
  } as never)
})

describe('open', () => {
  it('loads the project with its groups and task types', async () => {
    const store = await openedStore()

    expect(store.state).toBe('ready')
    expect(store.project).toEqual(project)
    expect(store.groups).toHaveLength(1)
    expect(store.taskTypes).toHaveLength(1)
    expect(projectsApi.listProjects).toHaveBeenCalledWith(7, { code: 'PRJ', page_size: 1 })
  })

  it('is not-found for an unknown project code', async () => {
    vi.mocked(projectsApi.listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 1,
    })

    const store = await openedStore()

    expect(store.state).toBe('not-found')
  })

  it('is an error when loading fails', async () => {
    vi.mocked(projectsApi.listProjects).mockRejectedValue(new Error('boom'))

    const store = await openedStore()

    expect(store.state).toBe('error')
  })
})

describe('loadFile', () => {
  it('shows the first sheet with nothing mapped yet', async () => {
    const store = await storeWithFile()

    expect(store.hasFile).toBe(true)
    expect(store.fileName).toBe('list.xlsx')
    expect(store.rows.map((row) => row.sheetRow)).toEqual([1, 3, 4])
    expect(store.mapping).toEqual([null, null, null])
    expect(store.fps).toBe(25)
  })

  it('collects the existing shot names from every page', async () => {
    vi.mocked(readSpreadsheet).mockResolvedValue([sheet()])
    vi.mocked(shotsApi.listShots)
      .mockResolvedValueOnce({ items: [shot('X'), shot('Y')], total: 3, page: 1, page_size: 2 })
      .mockResolvedValueOnce({ items: [shot('Z')], total: 3, page: 2, page_size: 2 })
    const store = await openedStore()

    await store.loadFile(new File([''], 'list.xlsx'))

    expect([...store.existingNames]).toEqual(['X', 'Y', 'Z'])
  })

  it('lets a failed read through and shows no file', async () => {
    vi.mocked(readSpreadsheet).mockRejectedValue(new Error('not a spreadsheet'))
    vi.mocked(shotsApi.listShots).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
    })
    const store = await openedStore()

    await expect(store.loadFile(new File([''], 'x.xlsx'))).rejects.toThrow()

    expect(store.hasFile).toBe(false)
    expect(store.isReadingFile).toBe(false)
  })

  it('switches sheets and starts the mapping over', async () => {
    vi.mocked(readSpreadsheet).mockResolvedValue([
      sheet(),
      { name: 'Лист2', columnCount: 1, rows: [] },
    ])
    vi.mocked(shotsApi.listShots).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
    })
    const store = await openedStore()
    await store.loadFile(new File([''], 'list.xlsx'))
    store.setField(0, 'name')

    store.selectSheet(1)

    expect(store.rows).toEqual([])
    expect(store.mapping).toEqual([null])
  })
})

describe('mapping and rows', () => {
  it('cannot submit until the name column is mapped', async () => {
    const store = await storeWithFile()
    expect(store.canSubmit).toBe(false)

    store.setField(0, 'name')

    // "шот" is the first row's name; skipping it leaves two good rows.
    expect(store.problems.size).toBe(0)
    expect(store.canSubmit).toBe(true)
    expect(store.shotCount).toBe(3)
  })

  it('moves a field when it is given to another column', async () => {
    const store = await storeWithFile()
    store.setField(0, 'name')

    store.setField(2, 'name')

    expect(store.mapping).toEqual([null, null, 'name'])
  })

  it('skipped rows are not counted and not checked', async () => {
    const store = await storeWithFile(['A'])
    store.setField(0, 'name')
    expect(store.canSubmit).toBe(false)
    expect(store.problems.has(1)).toBe(true)

    store.setSkipped([1], true)

    expect(store.problems.size).toBe(0)
    expect(store.shotCount).toBe(2)
    expect(store.skippedCount).toBe(1)
    expect(store.canSubmit).toBe(true)
  })

  it('needs a valid fps once a timecode column is mapped', async () => {
    const store = await storeWithFile()
    store.setField(0, 'name')
    store.setField(1, 'timecode')
    store.setSkipped([0], true)
    expect(store.canSubmit).toBe(true)

    store.fps = null

    expect(store.canSubmit).toBe(false)
  })

  it('edits a cell, so a bad name can be fixed', async () => {
    const store = await storeWithFile(['TAKEN'])
    store.setField(0, 'name')
    store.setSkipped([0], true)
    store.setCell(1, 0, 'TAKEN')
    expect(store.problems.has(1)).toBe(true)

    store.setCell(1, 0, 'A')

    expect(store.problems.size).toBe(0)
  })

  it('adds a group or a task to rows once and removes it again', async () => {
    const store = await storeWithFile()
    const task = { kind: 'new', name: 'Вставка', typeId: 3, typeName: 'Композ' } as const

    store.addGroup([1, 2], '01 СЕРИЯ')
    store.addGroup([1], '01 СЕРИЯ')
    store.addTask([1], task)
    store.addTask([1], task)
    store.addTask([1], { kind: 'existing', taskId: 5, name: 'Клинап', code: 'CLN1' })
    store.addTask([1], { kind: 'existing', taskId: 5, name: 'Клинап', code: 'CLN1' })

    expect(store.rows[1]!.groups).toEqual(['01 СЕРИЯ'])
    expect(store.rows[2]!.groups).toEqual(['01 СЕРИЯ'])
    expect(store.rows[1]!.tasks).toHaveLength(2)

    store.removeGroup(1, '01 СЕРИЯ')
    store.removeTask(1, 0)

    expect(store.rows[1]!.groups).toEqual([])
    expect(store.rows[1]!.tasks).toHaveLength(1)
  })

  it('lists the groups and tasks that rows were given but the project lacks', async () => {
    const store = await storeWithFile()
    const task = { kind: 'new', name: 'Вставка', typeId: 3, typeName: 'Композ' } as const

    // "01 СЕРИЯ" is a group of the project; the others are new.
    store.addGroup([1, 2], '01 СЕРИЯ')
    store.addGroup([1], '03 СЕРИЯ')
    store.addGroup([2], '02 СЕРИЯ')
    store.addGroup([2], '03 СЕРИЯ')
    store.addTask([1, 2], task)
    store.addTask([2], { kind: 'existing', taskId: 5, name: 'Клинап', code: 'CLN1' })

    expect(store.pendingGroups).toEqual(['02 СЕРИЯ', '03 СЕРИЯ'])
    expect(store.pendingTasks).toEqual([task])
  })

  it('does not list what only skipped rows would have created', async () => {
    const store = await storeWithFile()
    store.addGroup([1], '02 СЕРИЯ')
    store.addTask([1], { kind: 'new', name: 'Вставка', typeId: 3, typeName: 'Композ' })

    store.setSkipped([1], true)

    expect(store.pendingGroups).toEqual([])
    expect(store.pendingTasks).toEqual([])
  })

  it('forgets the file on reset', async () => {
    const store = await storeWithFile()

    store.reset()

    expect(store.hasFile).toBe(false)
    expect(store.rows).toEqual([])
  })
})

describe('submit', () => {
  async function readyToSubmit() {
    const store = await storeWithFile()
    store.setField(0, 'name')
    store.setField(1, 'timecode')
    store.setField(2, 'taskText')
    store.setSkipped([0], true)
    store.addGroup([1, 2], '01 СЕРИЯ')
    return store
  }

  it('sends the kept rows and returns the counts', async () => {
    const counts = { shots_created: 2, groups_created: 1, tasks_created: 0, messages_created: 1 }
    vi.mocked(shotImportApi.importShots).mockResolvedValue(counts)
    const store = await readyToSubmit()

    const result = await store.submit()

    expect(result).toEqual(counts)
    expect(shotImportApi.importShots).toHaveBeenCalledWith(1, {
      shots: [
        { name: 'A', rec_timecode: 30, groups: ['01 СЕРИЯ'], tasks: [], messages: ['вставка'] },
        { name: 'B', rec_timecode: null, groups: ['01 СЕРИЯ'], tasks: [], messages: [] },
      ],
    })
    expect(store.isSubmitting).toBe(false)
  })

  it('does nothing while there are problems', async () => {
    const store = await storeWithFile()

    expect(await store.submit()).toBeUndefined()
    expect(shotImportApi.importShots).not.toHaveBeenCalled()
  })

  it('puts the server problems on the rows, and an edit clears them', async () => {
    const error = new AxiosError('bad request', '400', undefined, undefined, {
      status: 400,
      data: {
        detail: [
          {
            msg: 'A shot with this name already exists in this project.',
            loc: ['shots', 1, 'name'],
          },
          { msg: 'This company has no default task status.', loc: ['shots'] },
        ],
      },
    } as never)
    vi.mocked(shotImportApi.importShots).mockRejectedValue(error)
    const store = await readyToSubmit()

    await expect(store.submit()).rejects.toBe(error)

    // Payload index 1 is the second kept row: row id 2.
    expect(store.problems.get(2)).toEqual(['Кадр с таким именем уже есть в проекте.'])
    expect(store.generalProblems).toEqual(['У компании не задан статус задач по умолчанию.'])
    expect(store.canSubmit).toBe(false)

    store.setCell(2, 0, 'B2')

    expect(store.problems.size).toBe(0)
    expect(store.canSubmit).toBe(true)
  })

  it('rethrows other errors without marking rows', async () => {
    vi.mocked(shotImportApi.importShots).mockRejectedValue(new Error('network'))
    const store = await readyToSubmit()

    await expect(store.submit()).rejects.toThrow('network')

    expect(store.problems.size).toBe(0)
    expect(store.isSubmitting).toBe(false)
  })
})
