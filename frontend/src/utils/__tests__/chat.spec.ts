import { describe, expect, it } from 'vitest'
import { describeSystemMessage, mergeLatestWindow, userName } from '@/utils/chat'
import type { MessageOut, UserOut } from '@/types/api'

function buildUser(overrides: Partial<UserOut> = {}): UserOut {
  return {
    id: 1,
    email: 'ivan@example.com',
    first_name: 'Иван',
    last_name: 'Петров',
    ...overrides,
  } as UserOut
}

function buildMessage(overrides: Partial<MessageOut> = {}): MessageOut {
  return {
    id: 1,
    shot_id: 10,
    type: 'user',
    text: 'Hello',
    event: null,
    payload: {},
    reply_to: null,
    versions: [],
    attachments: [],
    reactions: [],
    edited_at: null,
    created_by: buildUser(),
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function system(event: string, payload: Record<string, unknown>, by: UserOut | null = buildUser()) {
  return buildMessage({ type: 'system', text: '', event, payload, created_by: by })
}

describe('userName', () => {
  it('joins first and last name', () => {
    expect(userName(buildUser())).toBe('Иван Петров')
  })

  it('falls back to the e-mail for a user without a name', () => {
    expect(userName(buildUser({ first_name: '', last_name: '' }))).toBe('ivan@example.com')
  })

  it('names a deleted user generically', () => {
    expect(userName(null)).toBe('Кто-то')
  })
})

describe('describeSystemMessage', () => {
  it('describes an uploaded version', () => {
    const message = system('version_uploaded', { version_id: 3, version_name: 'PRJ_0010_v02' })

    expect(describeSystemMessage(message)).toBe('Иван Петров загрузил версию PRJ_0010_v02')
  })

  it('describes an added task', () => {
    const message = system('task_added', { task_code: 'CLN12', task_name: 'Roto' })

    expect(describeSystemMessage(message)).toBe('Иван Петров добавил задачу CLN12 «Roto»')
  })

  it('describes a status change', () => {
    const message = system('status_changed', {
      task_code: 'CLN12',
      from: { id: 1, name: 'Не начата' },
      to: { id: 2, name: 'В работе' },
    })

    expect(describeSystemMessage(message)).toBe(
      'Иван Петров сменил статус задачи CLN12: Не начата → В работе',
    )
  })

  it('describes assigning, replacing and removing an assignee', () => {
    const base = { task_code: 'CLN12' }
    const anna = { id: 5, name: 'Анна Смирнова' }
    const oleg = { id: 6, name: 'Олег Ким' }

    expect(
      describeSystemMessage(system('assignee_changed', { ...base, from: null, to: anna })),
    ).toBe('Иван Петров назначил исполнителем задачи CLN12: Анна Смирнова')
    expect(
      describeSystemMessage(system('assignee_changed', { ...base, from: anna, to: oleg })),
    ).toBe('Иван Петров сменил исполнителя задачи CLN12: Анна Смирнова → Олег Ким')
    expect(
      describeSystemMessage(system('assignee_changed', { ...base, from: anna, to: null })),
    ).toBe('Иван Петров снял исполнителя задачи CLN12 (был: Анна Смирнова)')
  })

  it('does not leave a blank for an assignee without a name', () => {
    const message = system('assignee_changed', {
      task_code: 'CLN12',
      from: null,
      to: { id: 5, name: '' },
    })

    expect(describeSystemMessage(message)).toBe(
      'Иван Петров назначил исполнителем задачи CLN12: без имени',
    )
  })

  it('still reads well when the actor user was deleted', () => {
    const message = system('version_uploaded', { version_name: 'v01' }, null)

    expect(describeSystemMessage(message)).toBe('Кто-то загрузил версию v01')
  })

  it('survives an unexpected payload shape', () => {
    const message = system('status_changed', {})

    expect(describeSystemMessage(message)).toContain('сменил статус задачи')
  })
})

describe('mergeLatestWindow', () => {
  const msg = (id: number, text = `m${id}`) => buildMessage({ id, text })

  it('appends new messages after the ones already held', () => {
    const result = mergeLatestWindow([msg(1), msg(2)], [msg(1), msg(2), msg(3)], false)

    expect(result.items.map((m) => m.id)).toEqual([1, 2, 3])
  })

  it('keeps older history that is outside the window and leaves hasOlder alone', () => {
    const held = [msg(1), msg(2), msg(3), msg(4)]

    const result = mergeLatestWindow(held, [msg(3), msg(4), msg(5)], true)

    expect(result.items.map((m) => m.id)).toEqual([1, 2, 3, 4, 5])
    expect(result.hasOlder).toBeNull()
  })

  it('shows edits made inside the window', () => {
    const result = mergeLatestWindow([msg(1), msg(2, 'old')], [msg(1), msg(2, 'edited')], false)

    expect(result.items.map((m) => m.text)).toEqual(['m1', 'edited'])
  })

  it('drops messages deleted inside the window', () => {
    const result = mergeLatestWindow([msg(1), msg(2), msg(3)], [msg(1), msg(3)], false)

    expect(result.items.map((m) => m.id)).toEqual([1, 3])
  })

  it('replaces everything when the window is the whole chat', () => {
    const result = mergeLatestWindow([msg(1), msg(2)], [msg(2)], false)

    expect(result.items.map((m) => m.id)).toEqual([2])
    expect(result.hasOlder).toBe(false)
  })

  it('replaces everything when so many arrived that the window starts after the last one held', () => {
    const result = mergeLatestWindow([msg(1), msg(2)], [msg(40), msg(41)], true)

    expect(result.items.map((m) => m.id)).toEqual([40, 41])
    expect(result.hasOlder).toBe(true)
  })

  it('clears an emptied chat', () => {
    const result = mergeLatestWindow([msg(1)], [], false)

    expect(result.items).toEqual([])
    expect(result.hasOlder).toBe(false)
  })
})
