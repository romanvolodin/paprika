export interface SheetRow {
  /** The row's number in the spreadsheet, starting from 1. */
  sheetRow: number
  cells: string[]
}

export interface SheetData {
  name: string
  rows: SheetRow[]
  columnCount: number
}

function isBlank(cells: string[]): boolean {
  return cells.every((cell) => cell.trim() === '')
}

/**
 * Turns a sheet's rows (any cell types) into text rows of equal width,
 * dropping the rows with nothing in them. Dropped rows keep their place
 * in the numbering, so row numbers still match the spreadsheet.
 */
export function normalizeSheet(name: string, rawRows: unknown[][]): SheetData {
  const textRows = rawRows.map((row) => row.map((cell) => String(cell ?? '')))
  const columnCount = Math.max(0, ...textRows.map((row) => row.length))
  const rows = textRows.flatMap((cells, index): SheetRow[] =>
    isBlank(cells)
      ? []
      : [
          {
            sheetRow: index + 1,
            cells: Array.from({ length: columnCount }, (_, column) => cells[column] ?? ''),
          },
        ],
  )
  return { name, rows, columnCount }
}

const TEXT_FILE_PATTERN = /\.(csv|tsv|txt)$/i

/**
 * Text files are decoded here instead of by the parser, which would
 * treat the bytes as Western European and garble Cyrillic. UTF-8 is
 * tried first; anything that isn't valid UTF-8 is taken for windows-1251,
 * which is what Excel on a Russian Windows saves a plain "CSV" in.
 */
function decodeText(bytes: Uint8Array): string {
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes)
  } catch {
    return new TextDecoder('windows-1251').decode(bytes)
  }
}

/**
 * Reads every sheet of an Excel / LibreOffice Calc / CSV file in the
 * browser. Cells come as the text the spreadsheet shows. The parser is
 * loaded on demand, so it only costs anything on the import page.
 */
export async function readSpreadsheet(file: File): Promise<SheetData[]> {
  const XLSX = await import('xlsx')
  const bytes = new Uint8Array(await file.arrayBuffer())
  const workbook = TEXT_FILE_PATTERN.test(file.name)
    ? XLSX.read(decodeText(bytes), { type: 'string' })
    : XLSX.read(bytes, { type: 'array' })
  return workbook.SheetNames.map((name) => {
    const sheet = workbook.Sheets[name]!
    const rawRows = XLSX.utils.sheet_to_json<unknown[]>(sheet, {
      header: 1,
      raw: false,
      defval: '',
      blankrows: true,
    })
    return normalizeSheet(name, rawRows)
  })
}
