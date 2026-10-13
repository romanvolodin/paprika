const SIZE_UNITS = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']

export function formatFileSize(bytes: number): string {
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < SIZE_UNITS.length - 1) {
    value /= 1024
    unit += 1
  }
  const text =
    unit === 0 ? String(value) : value.toLocaleString('ru-RU', { maximumFractionDigits: 1 })
  return `${text} ${SIZE_UNITS[unit]}`
}

/** "240 к. · 24 fps" for videos, "—" for images (no duration). */
export function formatVideoTiming(duration: number | null, fps: number | null): string {
  if (duration === null) return '—'
  const rate = fps === null ? '' : ` · ${Number(fps.toFixed(3))} fps`
  return `${duration} к.${rate}`
}
