import { computed, ref } from 'vue'
import * as chatApi from '@/api/chat'
import { describeChatAttachmentError } from '@/utils/apiError'
import type { AttachmentOut } from '@/types/api'

// Mirrors the backend's limit of files in one message
// (`CHAT_MESSAGE_MAX_ATTACHMENTS`), so the 11th is refused up front.
export const MAX_CHAT_ATTACHMENTS = 10

export interface ComposerFile {
  key: number
  name: string
  size: number
  /** 0-100, only meaningful while uploading. */
  progress: number
  status: 'uploading' | 'ready' | 'failed'
  attachment: AttachmentOut | null
  error: string | null
}

/**
 * The files being prepared for the next chat message: each one is
 * uploaded as soon as it is added, and sent later by id. Files that
 * never get sent (removed, or the shot was switched) are deleted from
 * the server on a best-effort basis.
 */
export function useChatAttachments(getShotId: () => number) {
  const files = ref<ComposerFile[]>([])
  let nextKey = 1

  const readyIds = computed(() =>
    files.value.flatMap((file) => (file.attachment ? [file.attachment.id] : [])),
  )
  const isUploading = computed(() => files.value.some((file) => file.status === 'uploading'))
  // A failed upload takes no slot: it is only a notice waiting to be dismissed.
  const activeCount = computed(() => files.value.filter((file) => file.status !== 'failed').length)

  async function discardOnServer(attachment: AttachmentOut) {
    try {
      await chatApi.deleteChatAttachment(attachment.id)
    } catch {
      // Best effort: an orphan left behind is harmless.
    }
  }

  async function upload(file: File, shotId: number) {
    const key = nextKey++
    files.value = [
      ...files.value,
      {
        key,
        name: file.name,
        size: file.size,
        progress: 0,
        status: 'uploading',
        attachment: null,
        error: null,
      },
    ]
    const update = (changes: Partial<ComposerFile>) => {
      files.value = files.value.map((item) => (item.key === key ? { ...item, ...changes } : item))
    }

    try {
      const attachment = await chatApi.uploadChatAttachment(shotId, file, (loaded, total) =>
        update({ progress: Math.round((loaded / total) * 100) }),
      )
      if (files.value.some((item) => item.key === key)) {
        update({ status: 'ready', attachment, progress: 100 })
      } else {
        // The chip was removed while the file was still on its way.
        await discardOnServer(attachment)
      }
    } catch (error) {
      update({ status: 'failed', error: describeChatAttachmentError(error) })
    }
  }

  /** Starts uploading what fits; returns how many files were left out. */
  function add(selected: File[]): number {
    const free = Math.max(0, MAX_CHAT_ATTACHMENTS - activeCount.value)
    const accepted = selected.slice(0, free)
    const shotId = getShotId()
    for (const file of accepted) {
      void upload(file, shotId)
    }
    return selected.length - accepted.length
  }

  async function remove(key: number) {
    const file = files.value.find((item) => item.key === key)
    if (!file) return
    files.value = files.value.filter((item) => item.key !== key)
    if (file.attachment) await discardOnServer(file.attachment)
  }

  /** Forgets the files without deleting them: they were sent. */
  function clear() {
    files.value = []
  }

  /** Drops everything, deleting the uploaded files that were never sent. */
  async function discardAll() {
    const pending = files.value
    files.value = []
    await Promise.all(
      pending.flatMap((file) => (file.attachment ? [discardOnServer(file.attachment)] : [])),
    )
  }

  return { files, readyIds, isUploading, add, remove, clear, discardAll }
}
