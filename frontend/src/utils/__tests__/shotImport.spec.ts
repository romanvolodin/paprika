import { describe, expect, it } from 'vitest'
import {
  buildPayload,
  cellText,
  createRows,
  emptyMapping,
  findProblems,
  mapServerProblems,
  rowsInRange,
  rowsWithSameTaskText,
  setColumnField,
  type ColumnMapping,
  type ImportRow,
} from '@/utils/shotImport'

function row(id: number, cells: string[], extra: Partial<ImportRow> = {}): ImportRow {
  return { id, sheetRow: id + 2, cells, skipped: false, groups: [], tasks: [], ...extra }
}

// name | timecode | task text | comment
const MAPPING: ColumnMapping = ['name', 'timecode', 'taskText', 'comment']
const OPTIONS = { fps: 25, existingNames: new Set<string>() }

describe('createRows', () => {
  it('numbers rows from 0 and keeps the sheet row numbers', () => {
    const rows = createRows({
      name: 'S',
      columnCount: 1,
      rows: [
        { sheetRow: 2, cells: ['a'] },
        { sheetRow: 7, cells: ['b'] },
      ],
    })

    expect(rows.map((r) => [r.id, r.sheetRow, r.skipped])).toEqual([
      [0, 2, false],
      [1, 7, false],
    ])
  })
})

describe('setColumnField', () => {
  it('assigns a field to a column', () => {
    expect(setColumnField(emptyMapping(3), 1, 'name')).toEqual([null, 'name', null])
  })

  it('takes the field away from the column that had it', () => {
    expect(setColumnField(['name', null, null], 2, 'name')).toEqual([null, null, 'name'])
  })

  it('replaces whatever the column had and can clear it', () => {
    expect(setColumnField(['name', 'comment'], 1, 'timecode')).toEqual(['name', 'timecode'])
    expect(setColumnField(['name', 'comment'], 1, null)).toEqual(['name', null])
  })
})

describe('cellText', () => {
  it('returns the trimmed cell of the mapped column, or an empty string', () => {
    const r = row(0, ['  A ', 'x'])

    expect(cellText(r, ['name', null], 'name')).toBe('A')
    expect(cellText(r, ['name', null], 'comment')).toBe('')
  })
})

describe('rowsWithSameTaskText', () => {
  const rows = [
    row(0, ['A', '', 'добавить пар', '']),
    row(1, ['B', '', 'добавить пар', '']),
    row(2, ['C', '', 'другое', '']),
    row(3, ['D', '', ' добавить пар ', ''], { skipped: true }),
    row(4, ['E', '', '', '']),
    row(5, ['F', '', '', '']),
  ]

  it('finds the rows with the same text, leaving skipped ones out', () => {
    expect(rowsWithSameTaskText(rows, MAPPING, 0)).toEqual([0, 1])
  })

  it('finds nothing for a row with no task text or without a task text column', () => {
    expect(rowsWithSameTaskText(rows, MAPPING, 4)).toEqual([])
    expect(rowsWithSameTaskText(rows, ['name', null, null, null], 0)).toEqual([])
    expect(rowsWithSameTaskText(rows, MAPPING, 99)).toEqual([])
  })
})

describe('rowsInRange', () => {
  // sheet rows: 2, 3, 4, 5
  const rows = [row(0, ['A']), row(1, ['B'], { skipped: true }), row(2, ['C']), row(3, ['D'])]

  it('takes the rows between two sheet row numbers that are not skipped', () => {
    expect(rowsInRange(rows, 2, 4)).toEqual([0, 2])
  })

  it('does not mind the order of the bounds', () => {
    expect(rowsInRange(rows, 5, 4)).toEqual([2, 3])
  })

  it('finds nothing outside the table', () => {
    expect(rowsInRange(rows, 100, 200)).toEqual([])
  })
})

describe('findProblems', () => {
  it('finds nothing wrong with good rows', () => {
    const rows = [row(0, ['A', '01:00:00:00', 'task', 'comment']), row(1, ['B', '', '', ''])]

    expect(findProblems(rows, MAPPING, OPTIONS).size).toBe(0)
  })

  it('flags a missing name and a name with whitespace or slashes', () => {
    const rows = [
      row(0, ['', '', '', '']),
      row(1, ['A B', '', '', '']),
      row(2, ['A/B', '', '', '']),
    ]

    const problems = findProblems(rows, MAPPING, OPTIONS)

    expect([...problems.keys()]).toEqual([0, 1, 2])
    expect(problems.get(0)).toEqual(['Нет имени кадра.'])
  })

  it('flags names that already exist in the project', () => {
    const problems = findProblems([row(0, ['TAKEN', '', '', ''])], MAPPING, {
      ...OPTIONS,
      existingNames: new Set(['TAKEN']),
    })

    expect(problems.get(0)).toEqual(['Кадр с таким именем уже есть в проекте.'])
  })

  it('flags a name repeated in the table from its second occurrence on', () => {
    const rows = [row(0, ['A', '', '', '']), row(1, ['A', '', '', '']), row(2, ['A', '', '', ''])]

    const problems = findProblems(rows, MAPPING, OPTIONS)

    expect([...problems.keys()]).toEqual([1, 2])
    expect(problems.get(1)![0]).toContain('строке 2')
  })

  it('does not count a skipped row as the first one of its name', () => {
    const rows = [row(0, ['A', '', '', ''], { skipped: true }), row(1, ['A', '', '', ''])]

    expect(findProblems(rows, MAPPING, OPTIONS).size).toBe(0)
  })

  it('never flags skipped rows', () => {
    const problems = findProblems(
      [row(0, ['', 'junk', '', ''], { skipped: true })],
      MAPPING,
      OPTIONS,
    )

    expect(problems.size).toBe(0)
  })

  it('flags a timecode that does not parse, and an empty one is fine', () => {
    const rows = [
      row(0, ['A', 'soon', '', '']),
      row(1, ['B', '', '', '']),
      row(2, ['C', '01:00:00:30', '', '']),
    ]

    const problems = findProblems(rows, MAPPING, OPTIONS)

    expect([...problems.keys()]).toEqual([0, 2])
  })

  it('does not look at the timecode when no column is mapped to it', () => {
    const problems = findProblems(
      [row(0, ['A', 'soon', '', ''])],
      ['name', null, null, null],
      OPTIONS,
    )

    expect(problems.size).toBe(0)
  })

  it('flags a chat message that is too long', () => {
    const problems = findProblems([row(0, ['A', '', 'x'.repeat(2001), ''])], MAPPING, OPTIONS)

    expect(problems.get(0)![0]).toContain('2000')
  })

  it('adds the problems the server reported', () => {
    const problems = findProblems([row(0, ['A', '', '', ''])], MAPPING, {
      ...OPTIONS,
      serverProblems: new Map([[0, ['Что-то не так.']]]),
    })

    expect(problems.get(0)).toEqual(['Что-то не так.'])
  })
})

describe('buildPayload', () => {
  it('builds the shots of the rows that are not skipped', () => {
    const rows = [
      row(0, ['A', '00:00:01:05', 'Текст задачи', 'Комментарий'], { groups: ['01 СЕРИЯ'] }),
      row(1, ['SKIPPED', '', '', ''], { skipped: true }),
      row(2, ['B', '', '', 'Только комментарий']),
    ]

    const { payload, rowIds } = buildPayload(rows, MAPPING, 25)

    expect(rowIds).toEqual([0, 2])
    expect(payload.shots).toEqual([
      {
        name: 'A',
        rec_timecode: 30,
        groups: ['01 СЕРИЯ'],
        tasks: [],
        messages: ['Текст задачи', 'Комментарий'],
      },
      { name: 'B', rec_timecode: null, groups: [], tasks: [], messages: ['Только комментарий'] },
    ])
  })

  it('sends existing tasks by id and new ones by name and type', () => {
    const rows = [
      row(0, ['A', '', '', ''], {
        tasks: [
          { kind: 'existing', taskId: 7, name: 'Клинап', code: 'CLN1234' },
          { kind: 'new', name: 'Вставка', typeId: 3, typeName: 'Композ' },
        ],
      }),
    ]

    const { payload } = buildPayload(rows, MAPPING, 25)

    expect(payload.shots[0]!.tasks).toEqual([{ task_id: 7 }, { name: 'Вставка', type_id: 3 }])
  })

  it('sends no timecode when the fps is not valid', () => {
    const { payload } = buildPayload([row(0, ['A', '00:00:01:05', '', ''])], MAPPING, null)

    expect(payload.shots[0]!.rec_timecode).toBeNull()
  })
})

describe('mapServerProblems', () => {
  it('puts each problem on the row its location points at', () => {
    const detail = [
      { msg: 'A shot with this name already exists in this project.', loc: ['shots', 1, 'name'] },
      {
        msg: 'Task with id=5 was not found in this project.',
        loc: ['shots', 0, 'tasks', 0, 'task_id'],
      },
    ]

    const { byRow, general } = mapServerProblems(detail, [10, 20])

    expect(byRow.get(20)).toEqual(['Кадр с таким именем уже есть в проекте.'])
    expect(byRow.get(10)).toEqual(['Задача не найдена в проекте.'])
    expect(general).toEqual([])
  })

  it('tells a missing task type from a missing task', () => {
    const detail = [
      {
        msg: "Task type with id=9 was not found in this project's company.",
        loc: ['shots', 0, 'tasks', 0, 'type_id'],
      },
    ]

    expect(mapServerProblems(detail, [1]).byRow.get(1)).toEqual([
      'Тип задачи не найден в компании.',
    ])
  })

  it('keeps problems without a row as general ones', () => {
    const { byRow, general } = mapServerProblems(
      [
        { msg: 'This company has no default shot status.', loc: ['shots'] },
        { msg: 'Odd', loc: ['x'] },
      ],
      [1],
    )

    expect(byRow.size).toBe(0)
    expect(general).toEqual(['У компании не задан статус кадров по умолчанию.', 'Odd'])
  })

  it('copes with a response that is not a list of problems', () => {
    expect(mapServerProblems(undefined, [1])).toEqual({ byRow: new Map(), general: [] })
  })
})
