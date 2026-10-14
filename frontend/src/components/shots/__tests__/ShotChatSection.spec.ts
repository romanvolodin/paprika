import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { AxiosError } from 'axios'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import ShotChatSection from '@/components/shots/ShotChatSection.vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import * as chatApi from '@/api/chat'
import type { MessageOut, UserOut } from '@/types/api'

vi.mock('@/api/chat')

const me = { id: 1, email: 'me@example.com', first_name: 'Иван', last_name: 'Петров' } as UserOut
const other = {
  id: 2,
  email: 'a@example.com',
  first_name: 'Анна',
  last_name: 'Смирнова',
} as UserOut

function buildMessage(id: number, overrides: Partial<MessageOut> = {}): MessageOut {
  return {
    id,
    shot_id: 10,
    type: 'user',
    text: `Message ${id}`,
    event: null,
    payload: {},
    reply_to: null,
    versions: [],
    attachments: [],
    reactions: [],
    edited_at: null,
    created_by: other,
    created_at: '2026-01-01T10:00:00Z',
    updated_at: '2026-01-01T10:00:00Z',
    ...overrides,
  }
}

function chatList(items: MessageOut[], hasOlder = false) {
  return { items, has_older: hasOlder, has_newer: false }
}

// The section needs naive-ui's message and dialog providers.
const Host = defineComponent({
  props: {
    shotId: { type: Number, required: true },
    canWrite: { type: Boolean, default: true },
  },
  setup(props) {
    return () =>
      h(NMessageProvider, null, {
        default: () =>
          h(NDialogProvider, null, {
            default: () => h(ShotChatSection, { shotId: props.shotId, canWrite: props.canWrite }),
          }),
      })
  },
})

describe('ShotChatSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useAuthStore().currentUser = me
    vi.clearAllMocks()
    vi.mocked(chatApi.listMessages).mockResolvedValue(
      chatList([
        buildMessage(1, { created_by: me, text: 'My own message' }),
        buildMessage(2, { text: "Someone else's message" }),
        buildMessage(3, {
          type: 'system',
          text: '',
          event: 'version_uploaded',
          payload: { version_name: 'PRJ_0010_v02' },
        }),
      ]),
    )
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows user messages and builds the sentence of system messages', async () => {
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    expect(chatApi.listMessages).toHaveBeenCalledWith(10, { limit: 50 })
    expect(wrapper.text()).toContain('My own message')
    expect(wrapper.text()).toContain("Someone else's message")
    expect(wrapper.text()).toContain('Анна Смирнова загрузил версию PRJ_0010_v02')
  })

  it('marks an edited message', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValue(
      chatList([buildMessage(1, { edited_at: '2026-01-01T11:00:00Z' })]),
    )

    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    expect(wrapper.text()).toContain('(изменено)')
  })

  it('offers edit and delete only on your own messages', async () => {
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    const own = wrapper.findAll('.shot-chat__message')[0]
    const foreign = wrapper.findAll('.shot-chat__message')[1]

    expect(own?.text()).toContain('Изменить')
    expect(own?.text()).toContain('Удалить')
    expect(foreign?.text()).not.toContain('Изменить')
    expect(foreign?.text()).not.toContain('Удалить')
  })

  it('shows no composer and no message actions to read-only members', async () => {
    const wrapper = mount(Host, { props: { shotId: 10, canWrite: false } })
    await flushPromises()

    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Отправить')
    expect(wrapper.text()).not.toContain('Изменить')
    expect(wrapper.text()).toContain('My own message')
  })

  it('sends the draft on Enter and clears it', async () => {
    vi.mocked(chatApi.sendMessage).mockResolvedValue(
      buildMessage(4, { created_by: me, text: 'Hello' }),
    )
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    const input = wrapper.find('textarea')
    await input.setValue('  Hello  ')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(chatApi.sendMessage).toHaveBeenCalledWith(10, { text: 'Hello' })
    expect((input.element as HTMLTextAreaElement).value).toBe('')
    expect(wrapper.text()).toContain('Hello')
  })

  it('does not send on Shift+Enter', async () => {
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    const input = wrapper.find('textarea')
    await input.setValue('line one')
    await input.trigger('keydown', { key: 'Enter', shiftKey: true })
    await flushPromises()

    expect(chatApi.sendMessage).not.toHaveBeenCalled()
  })

  it('does not send an empty draft', async () => {
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    const input = wrapper.find('textarea')
    await input.setValue('   ')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(chatApi.sendMessage).not.toHaveBeenCalled()
  })

  it('keeps the draft when sending fails', async () => {
    vi.mocked(chatApi.sendMessage).mockRejectedValue(new Error('network'))
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    const input = wrapper.find('textarea')
    await input.setValue('Hello')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect((input.element as HTMLTextAreaElement).value).toBe('Hello')
  })

  it('loads older messages on request', async () => {
    vi.mocked(chatApi.listMessages).mockResolvedValueOnce(
      chatList([buildMessage(51, { text: 'Newer' })], true),
    )
    vi.mocked(chatApi.listMessages).mockResolvedValueOnce(
      chatList([buildMessage(50, { text: 'Older' })], false),
    )
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    const button = wrapper.findAll('button').find((b) => b.text().includes('Показать более ранние'))
    await button?.trigger('click')
    await flushPromises()

    expect(chatApi.listMessages).toHaveBeenLastCalledWith(10, { limit: 50, before: 51 })
    expect(wrapper.text()).toContain('Older')
    expect(wrapper.text()).not.toContain('Показать более ранние')
  })

  // Moving from one shot page to another reuses the section with a new
  // shotId; the chat must follow it.
  it('reloads the chat when the shot changes', async () => {
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    vi.mocked(chatApi.listMessages).mockResolvedValue(
      chatList([buildMessage(9, { shot_id: 11, text: 'Other shot' })]),
    )
    await wrapper.setProps({ shotId: 11 })
    await flushPromises()

    expect(chatApi.listMessages).toHaveBeenLastCalledWith(11, { limit: 50 })
    expect(useChatStore().items.map((m) => m.shot_id)).toEqual([11])
  })

  describe('replies', () => {
    function findButton(wrapper: ReturnType<typeof mount>, text: string, scope?: Element) {
      const root = scope
        ? [...scope.querySelectorAll('button')]
        : wrapper.findAll('button').map((b) => b.element)
      return root.find((button) => button.textContent?.includes(text)) as HTMLElement | undefined
    }

    it('offers a reply button on every user message but not on system lines', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      const messages = wrapper.findAll('.shot-chat__message')
      expect(messages).toHaveLength(2)
      expect(messages.every((m) => m.text().includes('Ответить'))).toBe(true)
      expect(wrapper.find('.shot-chat__system-block').text()).not.toContain('Ответить')
    })

    it('shows who is being replied to and sends reply_to_id with the message', async () => {
      vi.mocked(chatApi.sendMessage).mockResolvedValue(buildMessage(4, { created_by: me }))
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      findButton(wrapper, 'Ответить', wrapper.findAll('.shot-chat__message')[1]?.element)?.click()
      await flushPromises()
      expect(wrapper.find('.shot-chat__reply-bar').text()).toContain('Ответ для Анна Смирнова')
      expect(wrapper.find('.shot-chat__reply-bar').text()).toContain("Someone else's message")

      const input = wrapper.find('textarea')
      await input.setValue('Thanks')
      await input.trigger('keydown', { key: 'Enter' })
      await flushPromises()

      expect(chatApi.sendMessage).toHaveBeenCalledWith(10, { text: 'Thanks', reply_to_id: 2 })
      expect(wrapper.find('.shot-chat__reply-bar').exists()).toBe(false)
    })

    it('cancels the reply without sending anything', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      findButton(wrapper, 'Ответить', wrapper.findAll('.shot-chat__message')[1]?.element)?.click()
      await flushPromises()

      await wrapper.find('.shot-chat__reply-bar button').trigger('click')

      expect(wrapper.find('.shot-chat__reply-bar').exists()).toBe(false)
      expect(chatApi.sendMessage).not.toHaveBeenCalled()
    })

    it('sends a plain message once the reply was cancelled', async () => {
      vi.mocked(chatApi.sendMessage).mockResolvedValue(buildMessage(4, { created_by: me }))
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      findButton(wrapper, 'Ответить', wrapper.findAll('.shot-chat__message')[1]?.element)?.click()
      await flushPromises()
      await wrapper.find('.shot-chat__reply-bar button').trigger('click')

      const input = wrapper.find('textarea')
      await input.setValue('Hi')
      await input.trigger('keydown', { key: 'Enter' })
      await flushPromises()

      expect(chatApi.sendMessage).toHaveBeenCalledWith(10, { text: 'Hi' })
    })

    it('drops the reply but keeps the text when the quoted message is gone', async () => {
      vi.mocked(chatApi.sendMessage).mockRejectedValue(
        new AxiosError('Bad request', 'ERR_BAD_REQUEST', undefined, undefined, {
          status: 400,
          data: { detail: [{ msg: "This message can't be replied to." }] },
        } as never),
      )
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      findButton(wrapper, 'Ответить', wrapper.findAll('.shot-chat__message')[1]?.element)?.click()
      await flushPromises()

      const input = wrapper.find('textarea')
      await input.setValue('Thanks')
      await input.trigger('keydown', { key: 'Enter' })
      await flushPromises()

      expect(wrapper.find('.shot-chat__reply-bar').exists()).toBe(false)
      expect((input.element as HTMLTextAreaElement).value).toBe('Thanks')
    })

    it('shows the quote of a reply, and a notice when the original was deleted', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValue(
        chatList([
          buildMessage(5, {
            text: 'My answer',
            reply_to: { id: 2, author: other, text: 'Original text', deleted: false },
          }),
          buildMessage(6, {
            text: 'Another answer',
            reply_to: { id: 3, author: other, text: '', deleted: true },
          }),
        ]),
      )
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      const quotes = wrapper.findAll('.shot-chat__quote')
      expect(quotes[0]?.text()).toContain('Анна Смирнова')
      expect(quotes[0]?.text()).toContain('Original text')
      expect(quotes[1]?.text()).toContain('Сообщение удалено')
    })

    it('does not offer replies to read-only members', async () => {
      const wrapper = mount(Host, { props: { shotId: 10, canWrite: false } })
      await flushPromises()

      expect(wrapper.text()).not.toContain('Ответить')
      expect(wrapper.find('.shot-chat__reply-bar').exists()).toBe(false)
    })
  })

  describe('reactions', () => {
    beforeEach(() => {
      vi.mocked(chatApi.listMessages).mockResolvedValue(
        chatList([
          buildMessage(1, {
            text: 'Reacted message',
            reactions: [
              { emoji: '👍', user_ids: [1, 2] },
              { emoji: '🔥', user_ids: [2] },
            ],
          }),
        ]),
      )
    })

    it('shows the reactions of a message with counts', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      const chips = wrapper.findAll('.chat-reactions__chip')
      expect(chips.map((chip) => chip.text())).toEqual(['👍2', '🔥1'])
      expect(chips[0]?.classes()).toContain('chat-reactions__chip--mine')
    })

    it('takes back your own reaction when you click it', async () => {
      vi.mocked(chatApi.removeReaction).mockResolvedValue({
        reactions: [
          { emoji: '👍', user_ids: [2] },
          { emoji: '🔥', user_ids: [2] },
        ],
      })
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      await wrapper.findAll('.chat-reactions__chip')[0]?.trigger('click')
      await flushPromises()

      expect(chatApi.removeReaction).toHaveBeenCalledWith(1, '👍')
      expect(chatApi.putReaction).not.toHaveBeenCalled()
      expect(wrapper.findAll('.chat-reactions__chip')[0]?.text()).toBe('👍1')
    })

    it('adds your reaction when you click an emoji you have not put', async () => {
      vi.mocked(chatApi.putReaction).mockResolvedValue({
        reactions: [
          { emoji: '👍', user_ids: [1, 2] },
          { emoji: '🔥', user_ids: [1, 2] },
        ],
      })
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      await wrapper.findAll('.chat-reactions__chip')[1]?.trigger('click')
      await flushPromises()

      expect(chatApi.putReaction).toHaveBeenCalledWith(1, '🔥')
      expect(wrapper.findAll('.chat-reactions__chip')[1]?.text()).toBe('🔥2')
    })

    it('keeps the counts when changing a reaction fails', async () => {
      vi.mocked(chatApi.putReaction).mockRejectedValue(new Error('network'))
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      await wrapper.findAll('.chat-reactions__chip')[1]?.trigger('click')
      await flushPromises()

      expect(wrapper.findAll('.chat-reactions__chip')[1]?.text()).toBe('🔥1')
    })

    it('shows reactions to read-only members but does not let them react', async () => {
      const wrapper = mount(Host, { props: { shotId: 10, canWrite: false } })
      await flushPromises()

      const chips = wrapper.findAll('.chat-reactions__chip')
      expect(chips).toHaveLength(2)
      expect(chips[0]?.attributes('disabled')).toBeDefined()
      expect(wrapper.find('.chat-reactions__add').exists()).toBe(false)
    })

    it('lets writers react to system messages too', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValue(
        chatList([
          buildMessage(3, {
            type: 'system',
            text: '',
            event: 'version_uploaded',
            payload: { version_name: 'v01' },
          }),
        ]),
      )
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      expect(wrapper.find('.shot-chat__system-block .chat-reactions__add').exists()).toBe(true)
    })
  })

  describe('polling', () => {
    it('asks for fresh messages every ten seconds while the page is visible', async () => {
      vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      vi.mocked(chatApi.listMessages).mockClear()

      vi.advanceTimersByTime(10_000)
      await flushPromises()
      expect(chatApi.listMessages).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(10_000)
      await flushPromises()
      expect(chatApi.listMessages).toHaveBeenCalledTimes(2)
      wrapper.unmount()
    })

    it('stops polling when the section goes away', async () => {
      vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      wrapper.unmount()
      vi.mocked(chatApi.listMessages).mockClear()

      vi.advanceTimersByTime(60_000)
      await flushPromises()

      expect(chatApi.listMessages).not.toHaveBeenCalled()
    })

    it('does not poll while the page is hidden', async () => {
      vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
      const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      vi.mocked(chatApi.listMessages).mockClear()

      vi.advanceTimersByTime(30_000)
      await flushPromises()

      expect(chatApi.listMessages).not.toHaveBeenCalled()
      visibility.mockRestore()
      wrapper.unmount()
    })
  })
})
