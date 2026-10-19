import type { ShotImportIn, ShotImportShotIn } from '@/types/api'
import type { SheetData } from '@/utils/spreadsheet'
import { parseTimecode } from '@/utils/timecode'

export type ImportField = 'name' | 'timecode' | 'taskText' | 'comment'

export const IMPORT_FIELDS: { value: ImportField; label: string }[] = [
  { value: 'name', label: 'Имя кадра' },
  { value: 'timecode', label: 'Таймкод начала' },
  { value: 'taskText', label: 'Текст задачи (в чат)' },
  { value: 'comment', label: 'Комментарий (в чат)' },
]

/** What each column of the sheet is saved into; null = ignored. */
export type ColumnMapping = (ImportField | null)[]

export type NewImportTask = { kind: 'new'; name: string; typeId: number; typeName: string }

export type ImportTask =
  { kind: 'existing'; taskId: number; name: string; code: string } | NewImportTask

export interface ImportRow {
  /** Stable key of the row within the import (not the sheet row number). */
  id: number
  sheetRow: number
  cells: string[]
  skipped: boolean
  groups: string[]
  tasks: ImportTask[]
}

const SHOT_NAME_PATTERN = /^[^/\s]+$/
const MIN_FPS = 1
const MAX_FPS = 240

/** The backend's default; the server's own check has the last word. */
export const MAX_MESSAGE_LENGTH = 2000

export function createRows(sheet: SheetData): ImportRow[] {
  return sheet.rows.map((row, index) => ({
    id: index,
    sheetRow: row.sheetRow,
    cells: [...row.cells],
    skipped: false,
    groups: [],
    tasks: [],
  }))
}

export function emptyMapping(columnCount: number): ColumnMapping {
  return Array.from({ length: columnCount }, () => null)
}

/**
 * Assigns `field` to `column` (or clears the column with null). A field
 * can live in one column only, so it is taken away from the column that
 * had it before.
 */
export function setColumnField(
  mapping: ColumnMapping,
  column: number,
  field: ImportField | null,
): ColumnMapping {
  return mapping.map((current, index) => {
    if (index === column) return field
    return field !== null && current === field ? null : current
  })
}

export function columnOf(mapping: ColumnMapping, field: ImportField): number {
  return mapping.indexOf(field)
}

export function cellText(row: ImportRow, mapping: ColumnMapping, field: ImportField): string {
  const column = columnOf(mapping, field)
  return column === -1 ? '' : (row.cells[column] ?? '').trim()
}

/**
 * Ids of the rows that are not skipped and have the same, non-empty
 * task text as the given row (the row itself included).
 */
export function rowsWithSameTaskText(
  rows: readonly ImportRow[],
  mapping: ColumnMapping,
  rowId: number,
): number[] {
  const source = rows.find((row) => row.id === rowId)
  const text = source ? cellText(source, mapping, 'taskText') : ''
  if (!text) return []
  return rows
    .filter((row) => !row.skipped && cellText(row, mapping, 'taskText') === text)
    .map((row) => row.id)
}

/**
 * Ids of the rows that are not skipped and whose sheet row number lies
 * between `from` and `to` (inclusive, in either order).
 */
export function rowsInRange(rows: readonly ImportRow[], from: number, to: number): number[] {
  const low = Math.min(from, to)
  const high = Math.max(from, to)
  return rows
    .filter((row) => !row.skipped && row.sheetRow >= low && row.sheetRow <= high)
    .map((row) => row.id)
}

export function isValidFps(fps: number | null): fps is number {
  return fps !== null && Number.isInteger(fps) && fps >= MIN_FPS && fps <= MAX_FPS
}

export interface ProblemOptions {
  fps: number | null
  existingNames: ReadonlySet<string>
  /** Messages the server sent back, by row id. */
  serverProblems?: ReadonlyMap<number, string[]>
}

/**
 * Everything wrong with the rows that would be imported, by row id.
 * Skipped rows are never a problem. A row is listed only if it has at
 * least one problem.
 */
export function findProblems(
  rows: readonly ImportRow[],
  mapping: ColumnMapping,
  options: ProblemOptions,
): Map<number, string[]> {
  const problems = new Map<number, string[]>()
  const add = (rowId: number, text: string) => {
    problems.set(rowId, [...(problems.get(rowId) ?? []), text])
  }

  const hasTimecode = columnOf(mapping, 'timecode') !== -1
  const firstRowOfName = new Map<string, number>()

  for (const row of rows) {
    if (row.skipped) continue

    const name = cellText(row, mapping, 'name')
    if (!name) {
      add(row.id, 'Нет имени кадра.')
    } else if (!SHOT_NAME_PATTERN.test(name)) {
      add(row.id, 'Имя не должно содержать пробелы и слэши.')
    } else if (options.existingNames.has(name)) {
      add(row.id, 'Кадр с таким именем уже есть в проекте.')
    } else if (firstRowOfName.has(name)) {
      add(row.id, `Имя повторяется в таблице (первый раз в строке ${firstRowOfName.get(name)}).`)
    } else {
      firstRowOfName.set(name, row.sheetRow)
    }

    const timecode = cellText(row, mapping, 'timecode')
    if (hasTimecode && timecode && isValidFps(options.fps)) {
      if (parseTimecode(timecode, options.fps) === null) {
        add(row.id, 'Не удалось разобрать таймкод.')
      }
    }

    for (const field of ['taskText', 'comment'] as const) {
      if (cellText(row, mapping, field).length > MAX_MESSAGE_LENGTH) {
        add(row.id, `Сообщение в чат длиннее ${MAX_MESSAGE_LENGTH} символов.`)
      }
    }

    for (const text of options.serverProblems?.get(row.id) ?? []) add(row.id, text)
  }

  return problems
}

export interface ImportPayload {
  payload: ShotImportIn
  /** Row id of every shot in `payload.shots`, in the same order. */
  rowIds: number[]
}

/**
 * The request body for the rows that are not skipped. The first
 * message is the task text, the second the comment; empty ones are
 * left out.
 */
export function buildPayload(
  rows: readonly ImportRow[],
  mapping: ColumnMapping,
  fps: number | null,
): ImportPayload {
  const kept = rows.filter((row) => !row.skipped)
  const shots = kept.map((row): ShotImportShotIn => {
    const timecode = cellText(row, mapping, 'timecode')
    return {
      name: cellText(row, mapping, 'name'),
      rec_timecode: timecode && isValidFps(fps) ? parseTimecode(timecode, fps) : null,
      groups: [...row.groups],
      tasks: row.tasks.map((task) =>
        task.kind === 'existing'
          ? { task_id: task.taskId }
          : { name: task.name, type_id: task.typeId },
      ),
      messages: (['taskText', 'comment'] as const)
        .map((field) => cellText(row, mapping, field))
        .filter((text) => text !== ''),
    }
  })
  return { payload: { shots }, rowIds: kept.map((row) => row.id) }
}

interface ServerErrorDetail {
  msg?: unknown
  loc?: unknown
}

export interface ServerProblems {
  /** By row id. */
  byRow: Map<number, string[]>
  /** Problems that belong to no particular row. */
  general: string[]
}

function translateServerMessage(message: string): string {
  if (message.includes('already exists')) return 'Кадр с таким именем уже есть в проекте.'
  if (message.includes("was not found in this project's company")) {
    return 'Тип задачи не найден в компании.'
  }
  if (message.includes('was not found in this project')) return 'Задача не найдена в проекте.'
  if (message.includes('no default shot status')) {
    return 'У компании не задан статус кадров по умолчанию.'
  }
  if (message.includes('no default task status')) {
    return 'У компании не задан статус задач по умолчанию.'
  }
  return message
}

/**
 * Sorts the server's 400 problems onto the rows they were about, using
 * the position in `loc` (`['shots', index, ...]`) and the row ids the
 * request was built from.
 */
export function mapServerProblems(detail: unknown, rowIds: readonly number[]): ServerProblems {
  const result: ServerProblems = { byRow: new Map(), general: [] }
  if (!Array.isArray(detail)) return result

  for (const entry of detail as ServerErrorDetail[]) {
    const message = translateServerMessage(typeof entry.msg === 'string' ? entry.msg : '')
    if (!message) continue
    const loc = Array.isArray(entry.loc) ? entry.loc : []
    const index = loc[0] === 'shots' && typeof loc[1] === 'number' ? loc[1] : null
    const rowId = index === null ? undefined : rowIds[index]
    if (rowId === undefined) {
      result.general.push(message)
    } else {
      result.byRow.set(rowId, [...(result.byRow.get(rowId) ?? []), message])
    }
  }
  return result
}
