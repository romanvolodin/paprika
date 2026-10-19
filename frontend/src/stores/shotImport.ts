import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { isAxiosError } from 'axios'
import * as projectsApi from '@/api/projects'
import * as shotImportApi from '@/api/shotImport'
import * as shotsApi from '@/api/shots'
import * as tasksApi from '@/api/tasks'
import {
  buildPayload,
  columnOf,
  createRows,
  emptyMapping,
  findProblems,
  isValidFps,
  mapServerProblems,
  setColumnField,
  type ColumnMapping,
  type ImportField,
  type ImportRow,
  type ImportTask,
} from '@/utils/shotImport'
import { readSpreadsheet, type SheetData } from '@/utils/spreadsheet'
import type {
  CompanyOut,
  ProjectMemberOut,
  ProjectOut,
  ShotGroupOut,
  ShotImportOut,
  TaskTypeOut,
} from '@/types/api'

export type ShotImportState = 'loading' | 'ready' | 'not-found' | 'error'

const MAX_PAGE_SIZE = 100
export const DEFAULT_FPS = 25

export const useShotImportStore = defineStore('shotImport', () => {
  const state = ref<ShotImportState>('loading')
  const project = ref<ProjectOut | null>(null)
  const members = ref<ProjectMemberOut[]>([])
  const groups = ref<ShotGroupOut[]>([])
  const taskTypes = ref<TaskTypeOut[]>([])

  const fileName = ref('')
  const sheets = ref<SheetData[]>([])
  const sheetIndex = ref(0)
  const rows = ref<ImportRow[]>([])
  const mapping = ref<ColumnMapping>([])
  const fps = ref<number | null>(DEFAULT_FPS)
  const existingNames = ref<Set<string>>(new Set())
  const serverProblems = ref<Map<number, string[]>>(new Map())
  const generalProblems = ref<string[]>([])
  const isReadingFile = ref(false)
  const isSubmitting = ref(false)

  // A newer `open` (or `loadFile`) call invalidates an earlier one still in flight.
  let openToken = 0
  let fileToken = 0

  const hasFile = computed(() => sheets.value.length > 0)
  const columnCount = computed(() => mapping.value.length)
  const hasNameColumn = computed(() => columnOf(mapping.value, 'name') !== -1)
  const hasTimecodeColumn = computed(() => columnOf(mapping.value, 'timecode') !== -1)
  const isFpsValid = computed(() => isValidFps(fps.value))

  const problems = computed(() =>
    findProblems(rows.value, mapping.value, {
      fps: fps.value,
      existingNames: existingNames.value,
      serverProblems: serverProblems.value,
    }),
  )
  const shotCount = computed(() => rows.value.filter((row) => !row.skipped).length)
  const skippedCount = computed(() => rows.value.length - shotCount.value)
  const canSubmit = computed(
    () =>
      hasNameColumn.value &&
      shotCount.value > 0 &&
      problems.value.size === 0 &&
      (!hasTimecodeColumn.value || isFpsValid.value) &&
      !isSubmitting.value,
  )

  async function open(company: CompanyOut, projectCode: string) {
    const token = ++openToken
    state.value = 'loading'
    project.value = null
    reset()

    try {
      const candidates = await projectsApi.listProjects(company.id, {
        code: projectCode,
        page_size: 1,
      })
      const found = candidates.items[0]
      if (token !== openToken) return
      if (!found) {
        state.value = 'not-found'
        return
      }

      const [memberList, groupList, typeList] = await Promise.all([
        projectsApi.listProjectMembers(found.id),
        shotsApi.listShotGroups(found.id, { page_size: MAX_PAGE_SIZE }),
        tasksApi.listTaskTypes(company.id),
      ])
      if (token !== openToken) return
      project.value = found
      members.value = memberList.items
      groups.value = groupList.items
      taskTypes.value = typeList.items
      state.value = 'ready'
    } catch (error) {
      if (token !== openToken) return
      state.value = isAxiosError(error) && error.response?.status === 404 ? 'not-found' : 'error'
    }
  }

  function reset() {
    fileToken++
    fileName.value = ''
    sheets.value = []
    sheetIndex.value = 0
    rows.value = []
    mapping.value = []
    fps.value = DEFAULT_FPS
    existingNames.value = new Set()
    serverProblems.value = new Map()
    generalProblems.value = []
    isReadingFile.value = false
  }

  async function fetchExistingNames(projectId: number): Promise<Set<string>> {
    const names = new Set<string>()
    for (let page = 1; ; page++) {
      const result = await shotsApi.listShots(projectId, { page, page_size: MAX_PAGE_SIZE })
      for (const shot of result.items) names.add(shot.name)
      if (result.items.length === 0 || names.size >= result.total) return names
    }
  }

  function selectSheet(index: number) {
    const sheet = sheets.value[index]
    if (!sheet) return
    sheetIndex.value = index
    rows.value = createRows(sheet)
    mapping.value = emptyMapping(sheet.columnCount)
    serverProblems.value = new Map()
    generalProblems.value = []
  }

  /**
   * Reads the file and shows its first sheet. Throws if the file can't
   * be read as a spreadsheet; the page shows the message.
   */
  async function loadFile(file: File) {
    if (!project.value) return
    const token = ++fileToken
    isReadingFile.value = true
    try {
      const [parsed, names] = await Promise.all([
        readSpreadsheet(file),
        fetchExistingNames(project.value.id),
      ])
      if (token !== fileToken) return
      fileName.value = file.name
      sheets.value = parsed
      existingNames.value = names
      selectSheet(0)
    } finally {
      if (token === fileToken) isReadingFile.value = false
    }
  }

  function setField(column: number, field: ImportField | null) {
    mapping.value = setColumnField(mapping.value, column, field)
    serverProblems.value = new Map()
  }

  function updateRows(ids: readonly number[], change: (row: ImportRow) => void) {
    const wanted = new Set(ids)
    for (const row of rows.value) if (wanted.has(row.id)) change(row)
    serverProblems.value = new Map()
  }

  function setSkipped(ids: readonly number[], skipped: boolean) {
    updateRows(ids, (row) => {
      row.skipped = skipped
    })
  }

  function setCell(rowId: number, column: number, value: string) {
    updateRows([rowId], (row) => {
      row.cells[column] = value
    })
  }

  function addGroup(ids: readonly number[], name: string) {
    updateRows(ids, (row) => {
      if (!row.groups.includes(name)) row.groups.push(name)
    })
  }

  function removeGroup(rowId: number, name: string) {
    updateRows([rowId], (row) => {
      row.groups = row.groups.filter((group) => group !== name)
    })
  }

  function sameTask(a: ImportTask, b: ImportTask): boolean {
    return a.kind === 'existing' && b.kind === 'existing'
      ? a.taskId === b.taskId
      : a.kind === 'new' && b.kind === 'new' && a.name === b.name && a.typeId === b.typeId
  }

  function addTask(ids: readonly number[], task: ImportTask) {
    updateRows(ids, (row) => {
      if (!row.tasks.some((existing) => sameTask(existing, task))) row.tasks.push({ ...task })
    })
  }

  function removeTask(rowId: number, index: number) {
    updateRows([rowId], (row) => {
      row.tasks.splice(index, 1)
    })
  }

  /**
   * Creates the shots. Resolves with the server's counts; on a 400 the
   * server's problems are put on the rows and the error is rethrown.
   */
  async function submit(): Promise<ShotImportOut | undefined> {
    if (!project.value || !canSubmit.value) return
    const { payload, rowIds } = buildPayload(rows.value, mapping.value, fps.value)
    isSubmitting.value = true
    serverProblems.value = new Map()
    generalProblems.value = []
    try {
      return await shotImportApi.importShots(project.value.id, payload)
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 400) {
        const sorted = mapServerProblems(error.response.data?.detail, rowIds)
        serverProblems.value = sorted.byRow
        generalProblems.value = sorted.general
      }
      throw error
    } finally {
      isSubmitting.value = false
    }
  }

  return {
    state,
    project,
    members,
    groups,
    taskTypes,
    fileName,
    sheets,
    sheetIndex,
    rows,
    mapping,
    fps,
    existingNames,
    serverProblems,
    generalProblems,
    isReadingFile,
    isSubmitting,
    hasFile,
    columnCount,
    hasNameColumn,
    hasTimecodeColumn,
    isFpsValid,
    problems,
    shotCount,
    skippedCount,
    canSubmit,
    open,
    reset,
    loadFile,
    selectSheet,
    setField,
    setSkipped,
    setCell,
    addGroup,
    removeGroup,
    addTask,
    removeTask,
    submit,
  }
})
