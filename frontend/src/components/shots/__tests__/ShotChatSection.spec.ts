import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { AxiosError } from 'axios'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NDialogProvider, NMessageProvider } from 'naive-ui'
import ShotChatSection from '@/components/shots/ShotChatSection.vue'
import UserAvatar from '@/components/common/UserAvatar.vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import * as chatApi from '@/api/chat'
import type { AttachmentOut, MessageOut, UserOut, VersionOut } from '@/types/api'

vi.mock('@/api/chat')
vi.mock('@/api/versions')

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

// A section left mounted keeps polling the shared mock every ten seconds.
enableAutoUnmount(afterEach)

// The menu of a message is drawn into the body, outside the wrapper.
function menuLabels(): string[] {
  return [...document.body.querySelectorAll('.n-dropdown-option-body__label')].map(
    (label) => label.textContent ?? '',
  )
}

async function openMenu(wrapper: ReturnType<typeof mount>, row: number) {
  await wrapper.findAll('.shot-chat__message')[row]?.find('.shot-chat__more').trigger('click')
  await flushPromises()
}

async function chooseAction(wrapper: ReturnType<typeof mount>, row: number, label: string) {
  await openMenu(wrapper, row)
  const option = [...document.body.querySelectorAll('.n-dropdown-option-body')].find((element) =>
    element.textContent?.includes(label),
  ) as HTMLElement
  option.click()
  await flushPromises()
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
    document.body.innerHTML = ''
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

    await openMenu(wrapper, 0)
    expect(menuLabels()).toEqual(['Ответить', 'Изменить', 'Удалить'])
  })

  it("offers only a reply on other people's messages", async () => {
    const wrapper = mount(Host, { props: { shotId: 10 } })
    await flushPromises()

    await openMenu(wrapper, 1)
    expect(menuLabels()).toEqual(['Ответить'])
  })

  it('shows no composer and no message actions to read-only members', async () => {
    const wrapper = mount(Host, { props: { shotId: 10, canWrite: false } })
    await flushPromises()

    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.find('button[aria-label="Отправить"]').exists()).toBe(false)
    expect(wrapper.find('.shot-chat__more').exists()).toBe(false)
    expect(wrapper.text()).toContain('My own message')
  })

  describe('composer', () => {
    it('is one row: a paperclip, the field and a round send button, nothing else', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      const row = wrapper.find('.shot-chat__composer')
      expect(row.findAll('button').map((button) => button.attributes('aria-label'))).toEqual([
        'Прикрепить файл',
        'Отправить',
      ])
      expect(row.find('textarea').attributes('placeholder')).toBe('Сообщение…')
    })

    it('has no way to attach a version to a message any more', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      expect(wrapper.find('button[aria-label="Приложить версию"]').exists()).toBe(false)
    })

    it('keeps the send button off while the field is empty', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      expect(wrapper.find('button[aria-label="Отправить"]').attributes('disabled')).toBeDefined()
    })

    it('sends with the arrow button', async () => {
      vi.mocked(chatApi.sendMessage).mockResolvedValue(buildMessage(9, { created_by: me }))
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      await wrapper.find('.shot-chat__composer textarea').setValue('Привет')

      await wrapper.find('button[aria-label="Отправить"]').trigger('click')
      await flushPromises()

      expect(chatApi.sendMessage).toHaveBeenCalledWith(10, { text: 'Привет' })
    })
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
    it('offers the menu with a reply on every user message but not on system lines', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      const messages = wrapper.findAll('.shot-chat__message')
      expect(messages).toHaveLength(2)
      expect(messages.every((m) => m.find('.shot-chat__more').exists())).toBe(true)
      expect(wrapper.find('.shot-chat__system-block .shot-chat__more').exists()).toBe(false)
    })

    it('shows who is being replied to and sends reply_to_id with the message', async () => {
      vi.mocked(chatApi.sendMessage).mockResolvedValue(buildMessage(4, { created_by: me }))
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      await chooseAction(wrapper, 1, 'Ответить')
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
      await chooseAction(wrapper, 1, 'Ответить')

      await wrapper.find('.shot-chat__reply-bar button').trigger('click')

      expect(wrapper.find('.shot-chat__reply-bar').exists()).toBe(false)
      expect(chatApi.sendMessage).not.toHaveBeenCalled()
    })

    it('sends a plain message once the reply was cancelled', async () => {
      vi.mocked(chatApi.sendMessage).mockResolvedValue(buildMessage(4, { created_by: me }))
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      await chooseAction(wrapper, 1, 'Ответить')
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
      await chooseAction(wrapper, 1, 'Ответить')

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

      expect(wrapper.find('.shot-chat__more').exists()).toBe(false)
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

    it('puts the reactions inside the bubble', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      expect(wrapper.find('.shot-chat__bubble .chat-reactions').exists()).toBe(true)
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

  describe('files and versions', () => {
    function buildAttachment(id: number, filename = `file${id}.png`): AttachmentOut {
      return {
        id,
        url: `http://localhost/media/${filename}`,
        filename,
        size: 2048,
        content_type: 'image/png',
      }
    }

    function buildVersion(id: number, name: string): VersionOut {
      return {
        id,
        project_id: 1,
        shot_id: 10,
        name,
        type: 'video',
        source: `http://localhost/media/${name}.mp4`,
        converted: null,
        thumb: null,
        width: 1920,
        height: 1080,
        duration: 240,
        fps: 24,
        codec: 'h264',
        file_size: 1024,
        created_by: null,
        updated_by: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }
    }

    function chooseFiles(wrapper: ReturnType<typeof mount>, files: File[]) {
      const input = wrapper.find('input[type="file"]')
      Object.defineProperty(input.element, 'files', { value: files, configurable: true })
      return input.trigger('change')
    }

    function buttonByLabel(wrapper: ReturnType<typeof mount>, label: string) {
      return wrapper.find(`button[aria-label="${label}"]`)
    }

    beforeEach(() => {
      let nextId = 1
      vi.mocked(chatApi.uploadChatAttachment).mockImplementation(async (_shot, upload) =>
        buildAttachment(nextId++, upload.name),
      )
      vi.mocked(chatApi.deleteChatAttachment).mockResolvedValue(undefined as never)
    })

    it('uploads the chosen files at once and lists them as chips', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      await chooseFiles(wrapper, [new File(['x'], 'a.png'), new File(['y'], 'b.mov')])
      await flushPromises()

      expect(chatApi.uploadChatAttachment).toHaveBeenCalledTimes(2)
      expect(vi.mocked(chatApi.uploadChatAttachment).mock.calls[0]?.[0]).toBe(10)
      const chips = wrapper.findAll('.shot-chat__chip')
      expect(chips.map((chip) => chip.text())).toEqual([
        expect.stringContaining('a.png'),
        expect.stringContaining('b.mov'),
      ])
    })

    it('sends the uploaded files by id and allows an empty text', async () => {
      vi.mocked(chatApi.sendMessage).mockResolvedValue(
        buildMessage(9, { created_by: me, text: '', attachments: [buildAttachment(1)] }),
      )
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      await chooseFiles(wrapper, [new File(['x'], 'a.png')])
      await flushPromises()

      const send = wrapper.find('button[aria-label="Отправить"]')
      expect(send?.attributes('disabled')).toBeUndefined()
      await send?.trigger('click')
      await flushPromises()

      expect(chatApi.sendMessage).toHaveBeenCalledWith(10, { text: '', attachment_ids: [1] })
      expect(wrapper.findAll('.shot-chat__chip')).toHaveLength(0)
      expect(chatApi.deleteChatAttachment).not.toHaveBeenCalled()
    })

    it('cannot send an empty message with nothing attached', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      const send = wrapper.find('button[aria-label="Отправить"]')

      expect(send?.attributes('disabled')).toBeDefined()
    })

    it('does not send while a file is still uploading', async () => {
      vi.mocked(chatApi.uploadChatAttachment).mockImplementationOnce(() => new Promise(() => {}))
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      await chooseFiles(wrapper, [new File(['x'], 'slow.mov')])
      await flushPromises()

      const input = wrapper.find('textarea')
      await input.setValue('Hello')
      await input.trigger('keydown', { key: 'Enter' })
      await flushPromises()

      expect(chatApi.sendMessage).not.toHaveBeenCalled()
      expect(wrapper.find('.shot-chat__chip').text()).toContain('0%')
    })

    it('deletes an unsent file from the server when its chip is removed', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      await chooseFiles(wrapper, [new File(['x'], 'a.png')])
      await flushPromises()

      await wrapper.find('.shot-chat__chip-remove').trigger('click')
      await flushPromises()

      expect(chatApi.deleteChatAttachment).toHaveBeenCalledWith(1)
      expect(wrapper.findAll('.shot-chat__chip')).toHaveLength(0)
    })

    it('warns and drops the files beyond ten in one message', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      await chooseFiles(
        wrapper,
        Array.from({ length: 11 }, (_, i) => new File(['x'], `f${i}.png`)),
      )
      await flushPromises()

      expect(chatApi.uploadChatAttachment).toHaveBeenCalledTimes(10)
      expect(wrapper.findAll('.shot-chat__chip')).toHaveLength(10)
    })

    it('shows the reason on a chip whose upload failed', async () => {
      vi.mocked(chatApi.uploadChatAttachment).mockRejectedValueOnce(new Error('network'))
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      await chooseFiles(wrapper, [new File(['x'], 'a.png')])
      await flushPromises()

      const chip = wrapper.find('.shot-chat__chip')
      expect(chip.classes()).toContain('shot-chat__chip--failed')
      expect(chip.text()).toContain('Не удалось загрузить файл.')
    })

    it('deletes the unsent files when the reader moves to another shot', async () => {
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      await chooseFiles(wrapper, [new File(['x'], 'a.png')])
      await flushPromises()

      await wrapper.setProps({ shotId: 11 })
      await flushPromises()

      expect(chatApi.deleteChatAttachment).toHaveBeenCalledWith(1)
      expect(wrapper.findAll('.shot-chat__chip')).toHaveLength(0)
    })

    it('shows the files and versions of a message in the feed, with no empty text line', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValue(
        chatList([
          buildMessage(1, {
            text: '',
            attachments: [buildAttachment(1, 'sky.png')],
            versions: [buildVersion(3, 'PRJ_0010_v02')],
          }),
        ]),
      )
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      expect(wrapper.find('.chat-files__image img').attributes('src')).toBe(
        'http://localhost/media/sky.png',
      )
      expect(wrapper.find('.chat-files__version').text()).toContain('PRJ_0010_v02')
      expect(wrapper.find('.shot-chat__text').exists()).toBe(false)
    })

    it('lets the author empty the text of a message that has files', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValue(
        chatList([
          buildMessage(1, { created_by: me, text: 'Caption', attachments: [buildAttachment(1)] }),
        ]),
      )
      vi.mocked(chatApi.editMessage).mockResolvedValue(
        buildMessage(1, { created_by: me, text: '', attachments: [buildAttachment(1)] }),
      )
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      await chooseAction(wrapper, 0, 'Изменить')
      await wrapper.find('.shot-chat__edit textarea').setValue('')
      const save = wrapper.findAll('button').find((b) => b.text().includes('Сохранить'))
      expect(save?.attributes('disabled')).toBeUndefined()
      await save?.trigger('click')
      await flushPromises()

      expect(chatApi.editMessage).toHaveBeenCalledWith(1, { text: '' })
    })

    it('does not let the author empty the text of a message without files', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValue(
        chatList([buildMessage(1, { created_by: me, text: 'Only text' })]),
      )
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()

      await chooseAction(wrapper, 0, 'Изменить')
      await wrapper.find('.shot-chat__edit textarea').setValue('  ')

      const save = wrapper.findAll('button').find((b) => b.text().includes('Сохранить'))
      expect(save?.attributes('disabled')).toBeDefined()
    })

    it('offers no attach controls to read-only members', async () => {
      const wrapper = mount(Host, { props: { shotId: 10, canWrite: false } })
      await flushPromises()

      expect(wrapper.find('input[type="file"]').exists()).toBe(false)
      expect(buttonByLabel(wrapper, 'Прикрепить файл').exists()).toBe(false)
      expect(buttonByLabel(wrapper, 'Отправить').exists()).toBe(false)
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

  describe('bubbles', () => {
    async function mountWith(items: MessageOut[]) {
      vi.mocked(chatApi.listMessages).mockResolvedValue(chatList(items))
      const wrapper = mount(Host, { props: { shotId: 10 } })
      await flushPromises()
      return wrapper
    }

    it("puts the user's own messages on the right and other people's on the left", async () => {
      const wrapper = await mountWith([
        buildMessage(1, { created_by: me }),
        buildMessage(2, { created_by: other, created_at: '2026-01-01T12:00:00Z' }),
      ])

      const rows = wrapper.findAll('.shot-chat__message')
      expect(rows[0].classes()).toContain('shot-chat__message--own')
      expect(rows[1].classes()).not.toContain('shot-chat__message--own')
    })

    it('shows the avatar of another author only next to the last message of a run', async () => {
      const wrapper = await mountWith([
        buildMessage(1, { created_at: '2026-01-01T10:00:00Z' }),
        buildMessage(2, { created_at: '2026-01-01T10:01:00Z' }),
        buildMessage(3, { created_by: me, created_at: '2026-01-01T10:02:00Z' }),
      ])

      const avatars = wrapper.findAllComponents(UserAvatar)
      expect(avatars).toHaveLength(1)
      const rows = wrapper.findAll('.shot-chat__message')
      expect(rows[1].findComponent(UserAvatar).exists()).toBe(true)
      expect(rows[0].findComponent(UserAvatar).exists()).toBe(false)
    })

    it('shows no avatar for the own messages', async () => {
      const wrapper = await mountWith([buildMessage(1, { created_by: me })])

      expect(wrapper.findComponent(UserAvatar).exists()).toBe(false)
    })

    it('names another author only above the first message of a run, and never the user', async () => {
      const wrapper = await mountWith([
        buildMessage(1, { created_at: '2026-01-01T10:00:00Z' }),
        buildMessage(2, { created_at: '2026-01-01T10:01:00Z' }),
        buildMessage(3, { created_by: me, created_at: '2026-01-01T10:02:00Z' }),
      ])

      const rows = wrapper.findAll('.shot-chat__message')
      expect(rows[0].find('.shot-chat__author').text()).toBe('Анна Смирнова')
      expect(rows[1].find('.shot-chat__author').exists()).toBe(false)
      expect(rows[2].find('.shot-chat__author').exists()).toBe(false)
    })

    it('shows the time of a message inside its bubble', async () => {
      const wrapper = await mountWith([buildMessage(1)])

      expect(wrapper.find('.shot-chat__stamp').text()).toMatch(/\d{2}:\d{2}/)
    })

    it('puts a heading above each new day', async () => {
      const wrapper = await mountWith([
        buildMessage(1, { created_at: '2026-01-01T10:00:00Z' }),
        buildMessage(2, { created_at: '2026-01-03T10:00:00Z' }),
        buildMessage(3, { created_at: '2026-01-03T10:01:00Z' }),
      ])

      expect(wrapper.findAll('.shot-chat__day')).toHaveLength(2)
    })

    it('opens the menu of a message on a right click, with the same actions', async () => {
      const wrapper = await mountWith([buildMessage(1, { created_by: me })])

      await wrapper.find('.shot-chat__bubble').trigger('contextmenu')
      await flushPromises()

      expect(menuLabels()).toEqual(['Ответить', 'Изменить', 'Удалить'])
    })

    it('does not take over the right click of a read-only member', async () => {
      vi.mocked(chatApi.listMessages).mockResolvedValue(chatList([buildMessage(1)]))
      const wrapper = mount(Host, { props: { shotId: 10, canWrite: false } })
      await flushPromises()

      await wrapper.find('.shot-chat__bubble').trigger('contextmenu')
      await flushPromises()

      expect(menuLabels()).toEqual([])
    })

    it('does not offer the menu on a message that is being edited', async () => {
      const wrapper = await mountWith([buildMessage(1, { created_by: me })])
      await chooseAction(wrapper, 0, 'Изменить')

      expect(wrapper.find('.shot-chat__more').exists()).toBe(false)
    })

    it('asks for a confirmation before deleting a message', async () => {
      vi.mocked(chatApi.deleteMessage).mockResolvedValue(undefined as never)
      const wrapper = await mountWith([buildMessage(1, { created_by: me })])

      await chooseAction(wrapper, 0, 'Удалить')

      expect(document.body.textContent).toContain('Удалить сообщение? Это действие необратимо.')
      expect(chatApi.deleteMessage).not.toHaveBeenCalled()
    })
  })
})
