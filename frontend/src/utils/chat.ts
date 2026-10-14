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
 * The sentence for a system message, built from its `event` and
 * `payload` (the backend stores ids and names as they were when the
 * event happened, so the line stays readable after things are renamed
 * or deleted).
 */
export function describeSystemMessage(message: MessageOut): string {
  const actor = userName(message.created_by)
  const payload = message.payload
  const task = `${str(payload.task_code)}`.trim()

  switch (message.event) {
    case 'version_uploaded':
      return `${actor} загрузил версию ${str(payload.version_name)}`
    case 'task_added':
      return `${actor} добавил задачу ${task} «${str(payload.task_name)}»`
    case 'status_changed':
      return `${actor} сменил статус задачи ${task}: ${refName(payload.from) ?? '—'} → ${refName(payload.to) ?? '—'}`
    case 'assignee_changed': {
      const from = refName(payload.from)
      const to = refName(payload.to)
      if (from === null && to !== null)
        return `${actor} назначил исполнителем задачи ${task}: ${to}`
      if (from !== null && to === null)
        return `${actor} снял исполнителя задачи ${task} (был: ${from})`
      return `${actor} сменил исполнителя задачи ${task}: ${from ?? '—'} → ${to ?? '—'}`
    }
    default:
      return `${actor} изменил кадр`
  }
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
