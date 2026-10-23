import type { MessageOut, UserOut } from '@/types/api'

/** The full name, the e-mail for a user without one, "Кто-то" for a deleted user. */
export function userName(user: Pick<UserOut, 'first_name' | 'last_name' | 'email'> | null): string {
  if (!user) return 'Кто-то'
  return `${user.first_name} ${user.last_name}`.trim() || user.email
}

function str(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

// `{ id, name }` references inside a payload; null when absent.
function refName(value: unknown): string | null {
  if (typeof value === 'object' && value !== null && 'name' in value) {
    return str((value as { name: unknown }).name) || 'без имени'
  }
  return null
}

/**
 * What happened, without the actor: "загрузил версию PRJ_0010_v02".
 * Built from an event's `event` and `payload` (the backend stores ids
 * and names as they were when the event happened, so the line stays
 * readable after things are renamed or deleted).
 */
export function describeEventAction(
  event: string | null,
  payload: Record<string, unknown>,
): string {
  const task = `${str(payload.task_code)}`.trim()

  switch (event) {
    case 'version_uploaded':
      return `загрузил версию ${str(payload.version_name)}`
    case 'task_added':
      return `добавил задачу ${task} «${str(payload.task_name)}»`
    case 'status_changed':
      return `сменил статус задачи ${task}: ${refName(payload.from) ?? '—'} → ${refName(payload.to) ?? '—'}`
    case 'assignee_changed': {
      const from = refName(payload.from)
      const to = refName(payload.to)
      if (from === null && to !== null) return `назначил исполнителем задачи ${task}: ${to}`
      if (from !== null && to === null) return `снял исполнителя задачи ${task} (был: ${from})`
      return `сменил исполнителя задачи ${task}: ${from ?? '—'} → ${to ?? '—'}`
    }
    default:
      return 'изменил кадр'
  }
}

/** The sentence for a system message: the actor and what they did. */
export function describeSystemMessage(message: MessageOut): string {
  return `${userName(message.created_by)} ${describeEventAction(message.event, message.payload)}`
}

/**
 * Folds a freshly fetched "latest window" of the chat into the messages
 * already held (oldest first), and says whether older history remains
 * (`null` - unchanged).
 *
 * Everything from the window's first message on is replaced by the
 * window, so edits and deletions inside it show up, while older
 * messages already loaded are kept. Two cases replace everything:
 * the window is the whole chat, or it starts after the last message
 * held - so many arrived that some were skipped, and the gap can't be
 * told apart from nothing, so the older history is reloaded on demand.
 */
export function mergeLatestWindow(
  current: MessageOut[],
  window: MessageOut[],
  windowHasOlder: boolean,
): { items: MessageOut[]; hasOlder: boolean | null } {
  const first = window[0]
  if (!first || !windowHasOlder) {
    return { items: window, hasOlder: false }
  }
  const last = current[current.length - 1]
  if (!last || first.id > last.id) {
    return { items: window, hasOlder: true }
  }
  return {
    items: [...current.filter((message) => message.id < first.id), ...window],
    hasOlder: null,
  }
}

/** Messages of one author closer than this form one run of bubbles. */
export const RUN_GAP_MS = 5 * 60 * 1000

export interface ChatEntry {
  message: MessageOut
  // The day heading to show above the message, null inside the same day.
  dayLabel: string | null
  firstOfRun: boolean
  lastOfRun: boolean
}

function dayKey(value: string): string {
  const date = new Date(value)
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

/** "Сегодня", "Вчера", "2 окт." (with the year for another year). */
export function formatDay(value: string, now: Date = new Date()): string {
  const date = new Date(value)
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (dayKey(value) === dayKey(now.toISOString())) return 'Сегодня'
  if (dayKey(value) === dayKey(yesterday.toISOString())) return 'Вчера'
  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
    ...(date.getFullYear() === now.getFullYear() ? {} : { year: 'numeric' }),
  })
}

/** "14:20" */
export function formatClock(value: string): string {
  return new Date(value).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

function inSameRun(a: MessageOut | undefined, b: MessageOut): boolean {
  return (
    a !== undefined &&
    a.type === 'user' &&
    b.type === 'user' &&
    a.created_by !== null &&
    a.created_by.id === b.created_by?.id &&
    dayKey(a.created_at) === dayKey(b.created_at) &&
    Math.abs(new Date(b.created_at).getTime() - new Date(a.created_at).getTime()) <= RUN_GAP_MS
  )
}

/**
 * The feed with what the bubbles need: where a new day starts and where
 * a run of messages by one author begins and ends (the name goes above
 * the first, the avatar next to the last).
 */
export function buildChatEntries(messages: MessageOut[], now: Date = new Date()): ChatEntry[] {
  return messages.map((message, index) => {
    const previous = messages[index - 1]
    const next = messages[index + 1]
    const newDay = !previous || dayKey(previous.created_at) !== dayKey(message.created_at)
    return {
      message,
      dayLabel: newDay ? formatDay(message.created_at, now) : null,
      firstOfRun: !inSameRun(previous, message),
      lastOfRun: !next || !inSameRun(message, next),
    }
  })
}
