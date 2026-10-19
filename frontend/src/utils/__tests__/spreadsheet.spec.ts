import { describe, expect, it } from 'vitest'
import * as XLSX from 'xlsx'
import { normalizeSheet, readSpreadsheet } from '@/utils/spreadsheet'

function fileFromRows(rows: unknown[][], bookType: XLSX.BookType, name: string): File {
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(rows), 'Первый')
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet([['x']]), 'Второй')
  const data = XLSX.write(workbook, { type: 'array', bookType }) as ArrayBuffer
  return new File([data], name)
}

describe('normalizeSheet', () => {
  it('drops empty rows but keeps the spreadsheet row numbers', () => {
    const sheet = normalizeSheet('S', [['шот', 'ТК'], [], ['', ' '], ['A', '01:00:00:00']])

    expect(sheet.rows.map((row) => row.sheetRow)).toEqual([1, 4])
  })

  it('pads rows to the same width and turns cells into text', () => {
    const sheet = normalizeSheet('S', [['a'], ['b', 2, null]])

    expect(sheet.columnCount).toBe(3)
    expect(sheet.rows.map((row) => row.cells)).toEqual([
      ['a', '', ''],
      ['b', '2', ''],
    ])
  })

  it('handles a sheet with nothing in it', () => {
    expect(normalizeSheet('S', [])).toEqual({ name: 'S', rows: [], columnCount: 0 })
  })
})

describe('readSpreadsheet', () => {
  const rows = [['шот', 'ТК', 'задача'], [], ['VRG_01_0150', '01:21:46:22', 'Зум с клиенткой']]

  it('reads every sheet of an xlsx file', async () => {
    const sheets = await readSpreadsheet(fileFromRows(rows, 'xlsx', 'list.xlsx'))

    expect(sheets.map((sheet) => sheet.name)).toEqual(['Первый', 'Второй'])
    expect(sheets[0]!.rows).toEqual([
      { sheetRow: 1, cells: ['шот', 'ТК', 'задача'] },
      { sheetRow: 3, cells: ['VRG_01_0150', '01:21:46:22', 'Зум с клиенткой'] },
    ])
  })

  it('reads an ods file', async () => {
    const sheets = await readSpreadsheet(fileFromRows(rows, 'ods', 'list.ods'))

    expect(sheets[0]!.rows[1]!.cells[0]).toBe('VRG_01_0150')
  })

  it('reads a semicolon-separated csv file', async () => {
    const file = new File(['шот;ТК\nA;01:00:00:00\n'], 'list.csv')

    const sheets = await readSpreadsheet(file)

    expect(sheets[0]!.rows.map((row) => row.cells)).toEqual([
      ['шот', 'ТК'],
      ['A', '01:00:00:00'],
    ])
  })

  it('reads a csv file saved in windows-1251', async () => {
    // Cyrillic letters sit in 0xC0-0xFF there, in the same order as in Unicode.
    const encode = (text: string) =>
      Uint8Array.from(text, (char) =>
        char >= 'А' && char <= 'я' ? char.charCodeAt(0) - 0x410 + 0xc0 : char.charCodeAt(0),
      )
    const file = new File([encode('шот;задача\nA;вставка в монитор\n')], 'list.csv')

    const sheets = await readSpreadsheet(file)

    expect(sheets[0]!.rows.map((row) => row.cells)).toEqual([
      ['шот', 'задача'],
      ['A', 'вставка в монитор'],
    ])
  })

  it('reads a csv file', async () => {
    const file = new File(['шот,ТК\nA,01:00:00:00\n'], 'list.csv')

    const sheets = await readSpreadsheet(file)

    expect(sheets).toHaveLength(1)
    expect(sheets[0]!.rows.map((row) => row.cells)).toEqual([
      ['шот', 'ТК'],
      ['A', '01:00:00:00'],
    ])
  })
})
