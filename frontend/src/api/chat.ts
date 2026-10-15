import { apiClient } from './client'
import type {
  AttachmentOut,
  ChatListOut,
  ChatListQuery,
  MessageCreateIn,
  MessageOut,
  MessageUpdateIn,
  ReactionsOut,
} from '@/types/api'

export function listMessages(shotId: number, query: ChatListQuery = {}) {
  return apiClient
    .get<ChatListOut>(`/shots/${shotId}/chat/`, { params: query })
    .then((res) => res.data)
}

export function sendMessage(shotId: number, input: MessageCreateIn) {
  return apiClient.post<MessageOut>(`/shots/${shotId}/chat/`, input).then((res) => res.data)
}

export function editMessage(messageId: number, input: MessageUpdateIn) {
  return apiClient.patch<MessageOut>(`/chat/${messageId}/`, input).then((res) => res.data)
}

export function deleteMessage(messageId: number) {
  return apiClient.delete<void>(`/chat/${messageId}/`)
}

export function putReaction(messageId: number, emoji: string) {
  return apiClient
    .put<ReactionsOut>(`/chat/${messageId}/reactions/`, { emoji })
    .then((res) => res.data)
}

export function removeReaction(messageId: number, emoji: string) {
  return apiClient
    .delete<ReactionsOut>(`/chat/${messageId}/reactions/`, { params: { emoji } })
    .then((res) => res.data)
}

/**
 * Uploads a file to the shot's chat without sending it: the returned
 * attachment is later sent by its id together with a message.
 */
export function uploadChatAttachment(
  shotId: number,
  file: File,
  onProgress?: (loaded: number, total: number) => void,
) {
  const form = new FormData()
  form.append('file', file)
  return apiClient
    .post<AttachmentOut>(`/shots/${shotId}/chat/attachments/`, form, {
      onUploadProgress: (event) => {
        if (event.total) onProgress?.(event.loaded, event.total)
      },
    })
    .then((res) => res.data)
}

export function deleteChatAttachment(attachmentId: number) {
  return apiClient.delete<void>(`/chat/attachments/${attachmentId}/`)
}
