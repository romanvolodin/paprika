import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { AxiosError } from 'axios'
import { MAX_CHAT_ATTACHMENTS, useChatAttachments } from '@/composables/useChatAttachments'
import * as chatApi from '@/api/chat'
import type { AttachmentOut } from '@/types/api'

vi.mock('@/api/chat')

function buildAttachment(id: number, filename = `file${id}.png`): AttachmentOut {
  return {
    id,
    url: `http://localhost/media/${filename}`,
    filename,
    size: 2048,
    content_type: 'image/png',
  }
}

function file(name: string) {
  return new File(['x'], name)
}

type Upload = Awaited<ReturnType<typeof chatApi.uploadChatAttachment>>

describe('useChatAttachments', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    let nextId = 1
    vi.mocked(chatApi.uploadChatAttachment).mockImplementation(async (_shot, upload) =>
      buildAttachment(nextId++, upload.name),
    )
    vi.mocked(chatApi.deleteChatAttachment).mockResolvedValue(undefined as never)
  })

  it('uploads a added file to the current shot and keeps its attachment id', async () => {
    const attachments = useChatAttachments(() => 10)

    attachments.add([file('a.png')])
    await flushPromises()

    expect(chatApi.uploadChatAttachment).toHaveBeenCalledWith(
      10,
      expect.any(File),
      expect.any(Function),
    )
    expect(attachments.files.value).toHaveLength(1)
    expect(attachments.files.value[0]).toMatchObject({
      name: 'a.png',
      status: 'ready',
      progress: 100,
    })
    expect(attachments.readyIds.value).toEqual([1])
    expect(attachments.isUploading.value).toBe(false)
  })

  it('shows a file as uploading with its progress until the server answers', async () => {
    let finish!: (value: Upload) => void
    let report!: (loaded: number, total: number) => void
    vi.mocked(chatApi.uploadChatAttachment).mockImplementationOnce((_shot, _file, onProgress) => {
      report = onProgress as typeof report
      return new Promise((resolve) => {
        finish = resolve
      })
    })
    const attachments = useChatAttachments(() => 10)

    attachments.add([file('big.mov')])
    report(25, 100)

    expect(attachments.isUploading.value).toBe(true)
    expect(attachments.files.value[0]).toMatchObject({ status: 'uploading', progress: 25 })
    expect(attachments.readyIds.value).toEqual([])

    finish(buildAttachment(7, 'big.mov'))
    await flushPromises()
    expect(attachments.isUploading.value).toBe(false)
    expect(attachments.readyIds.value).toEqual([7])
  })

  it('refuses files beyond the per-message limit and reports how many were left out', async () => {
    const attachments = useChatAttachments(() => 10)
    const twelve = Array.from({ length: 12 }, (_, i) => file(`f${i}.png`))

    const skipped = attachments.add(twelve)
    await flushPromises()

    expect(skipped).toBe(2)
    expect(attachments.files.value).toHaveLength(MAX_CHAT_ATTACHMENTS)
    expect(chatApi.uploadChatAttachment).toHaveBeenCalledTimes(MAX_CHAT_ATTACHMENTS)
  })

  it('counts files already added against the limit', async () => {
    const attachments = useChatAttachments(() => 10)
    attachments.add(Array.from({ length: 8 }, (_, i) => file(`a${i}.png`)))
    await flushPromises()

    const skipped = attachments.add([file('b1.png'), file('b2.png'), file('b3.png')])

    expect(skipped).toBe(1)
  })

  it('keeps a failed upload as a notice with the reason, and it takes no slot', async () => {
    vi.mocked(chatApi.uploadChatAttachment).mockRejectedValueOnce(
      new AxiosError('Too large', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 413,
        data: { detail: [{ msg: 'The file is too large. Max size is 100 MB.' }] },
      } as never),
    )
    const attachments = useChatAttachments(() => 10)

    attachments.add([file('huge.mov')])
    await flushPromises()

    expect(attachments.files.value[0]).toMatchObject({ status: 'failed' })
    expect(attachments.files.value[0]?.error).toContain('100 МБ')
    expect(attachments.readyIds.value).toEqual([])
    expect(attachments.add(Array.from({ length: 10 }, (_, i) => file(`n${i}.png`)))).toBe(0)
  })

  it('removing an uploaded file deletes it on the server', async () => {
    const attachments = useChatAttachments(() => 10)
    attachments.add([file('a.png')])
    await flushPromises()

    await attachments.remove(attachments.files.value[0]!.key)

    expect(chatApi.deleteChatAttachment).toHaveBeenCalledWith(1)
    expect(attachments.files.value).toEqual([])
  })

  it('removing a failed file just drops it', async () => {
    vi.mocked(chatApi.uploadChatAttachment).mockRejectedValueOnce(new Error('network'))
    const attachments = useChatAttachments(() => 10)
    attachments.add([file('a.png')])
    await flushPromises()

    await attachments.remove(attachments.files.value[0]!.key)

    expect(chatApi.deleteChatAttachment).not.toHaveBeenCalled()
    expect(attachments.files.value).toEqual([])
  })

  it('a file removed while still uploading is deleted once it arrives', async () => {
    let finish!: (value: Upload) => void
    vi.mocked(chatApi.uploadChatAttachment).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    const attachments = useChatAttachments(() => 10)
    attachments.add([file('a.png')])

    await attachments.remove(attachments.files.value[0]!.key)
    expect(chatApi.deleteChatAttachment).not.toHaveBeenCalled()
    finish(buildAttachment(9))
    await flushPromises()

    expect(chatApi.deleteChatAttachment).toHaveBeenCalledWith(9)
    expect(attachments.files.value).toEqual([])
  })

  it('discardAll empties the list and deletes the uploaded files on the server', async () => {
    const attachments = useChatAttachments(() => 10)
    attachments.add([file('a.png'), file('b.png')])
    await flushPromises()

    await attachments.discardAll()

    expect(attachments.files.value).toEqual([])
    expect(chatApi.deleteChatAttachment).toHaveBeenCalledTimes(2)
  })

  it('clear forgets the files without deleting them, they were sent', async () => {
    const attachments = useChatAttachments(() => 10)
    attachments.add([file('a.png')])
    await flushPromises()

    attachments.clear()

    expect(attachments.files.value).toEqual([])
    expect(chatApi.deleteChatAttachment).not.toHaveBeenCalled()
  })

  it('a failed deletion on the server does not stop the file from being removed', async () => {
    vi.mocked(chatApi.deleteChatAttachment).mockRejectedValue(new Error('conflict'))
    const attachments = useChatAttachments(() => 10)
    attachments.add([file('a.png')])
    await flushPromises()

    await attachments.remove(attachments.files.value[0]!.key)

    expect(attachments.files.value).toEqual([])
  })

  it('uploads to the shot that was current when the file was added', async () => {
    let shotId = 10
    const attachments = useChatAttachments(() => shotId)

    attachments.add([file('a.png')])
    shotId = 11
    attachments.add([file('b.png')])
    await flushPromises()

    expect(vi.mocked(chatApi.uploadChatAttachment).mock.calls.map((call) => call[0])).toEqual([
      10, 11,
    ])
  })
})
