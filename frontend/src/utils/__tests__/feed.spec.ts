import { describe, expect, it } from 'vitest'
import { describeTypeFilter, groupFeedByDay } from '@/utils/feed'
import type { FeedItemOut } from '@/types/api'

function item(key: string, createdAt: string): FeedItemOut {
  return {
    key,
    type: 'chat',
    created_at: createdAt,
    created_by: null,
    shot: { id: 1, name: '0010' },
    text: 'Привет',
    attachments: [],
    versions: [],
    version: null,
    event: null,
    payload: {},
  }
}

describe('describeTypeFilter', () => {
  it('says "Все события" for no filter and for every type', () => {
    expect(describeTypeFilter([])).toBe('Все события')
    expect(describeTypeFilter(['chat', 'version', 'task'])).toBe('Все события')
  })

  it('names a single type', () => {
    expect(describeTypeFilter(['version'])).toBe('Версии')
  })

  it('counts several types', () => {
    expect(describeTypeFilter(['chat', 'version'])).toBe('2 события')
  })
})

describe('groupFeedByDay', () => {
  const now = new Date(2026, 9, 22, 15, 0)

  it('groups neighbours of the same day and keeps the order', () => {
    const days = groupFeedByDay(
      [
        item('a', new Date(2026, 9, 22, 12, 0).toISOString()),
        item('b', new Date(2026, 9, 22, 9, 0).toISOString()),
        item('c', new Date(2026, 9, 21, 18, 0).toISOString()),
        item('d', new Date(2026, 9, 13, 18, 0).toISOString()),
      ],
      now,
    )

    expect(days.map((day) => day.label)).toEqual([
      'Сегодня',
      'Вчера',
      expect.stringContaining('13'),
    ])
    expect(days.map((day) => day.items.map((i) => i.key))).toEqual([['a', 'b'], ['c'], ['d']])
  })

  it('is empty for an empty feed', () => {
    expect(groupFeedByDay([], now)).toEqual([])
  })
})
