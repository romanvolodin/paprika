import { formatDay } from '@/utils/chat'
import type { FeedEventType, FeedItemOut } from '@/types/api'

export const FEED_TYPE_LABELS: Record<FeedEventType, string> = {
  chat: 'Сообщения',
  version: 'Версии',
  task: 'Задачи',
}

/** "Все события", the one chosen type, or "2 события". */
export function describeTypeFilter(types: FeedEventType[]): string {
  if (types.length === 0 || types.length === Object.keys(FEED_TYPE_LABELS).length) {
    return 'Все события'
  }
  const [only] = types
  if (types.length === 1 && only) return FEED_TYPE_LABELS[only]
  return `${types.length} события`
}

export interface FeedDay {
  label: string
  items: FeedItemOut[]
}

/** Groups the feed (newest first) by calendar day, keeping the order. */
export function groupFeedByDay(items: FeedItemOut[], now: Date = new Date()): FeedDay[] {
  const days: FeedDay[] = []
  for (const item of items) {
    const label = formatDay(item.created_at, now)
    const last = days[days.length - 1]
    if (last && last.label === label) last.items.push(item)
    else days.push({ label, items: [item] })
  }
  return days
}
