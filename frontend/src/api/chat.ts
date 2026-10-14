import { apiClient } from './client'
import type {
  ChatListOut,
  ChatListQuery,
  MessageCreateIn,
  MessageOut,
  MessageUpdateIn,
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
