const TIMECODE_PATTERN = /^(\d{1,3})[\s:;.]+(\d{1,2})[\s:;.]+(\d{1,2})[\s:;.]+(\d{1,3})$/

/**
 * Turns a timecode like `08:01:35:12` (or `08 01 35 12`) into an absolute
 * frame count from `00:00:00:00`, hours included. Returns null if the text
 * isn't a valid timecode for the given fps (minutes and seconds under 60,
 * frames under fps).
 */
export function parseTimecode(text: string, fps: number): number | null {
  const match = TIMECODE_PATTERN.exec(text.trim())
  if (!match) return null
  const [hours, minutes, seconds, frames] = match.slice(1).map(Number) as [
    number,
    number,
    number,
    number,
  ]
  if (minutes >= 60 || seconds >= 60 || frames >= fps) return null
  return ((hours * 60 + minutes) * 60 + seconds) * fps + frames
}
