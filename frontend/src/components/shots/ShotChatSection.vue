<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useDocumentVisibility, useIntervalFn } from '@vueuse/core'
import { NButton, NInput, useDialog, useMessage } from 'naive-ui'
import ChatReactions from '@/components/shots/ChatReactions.vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { describeSystemMessage, userName } from '@/utils/chat'
import { firstValidationMessage } from '@/utils/apiError'
import type { MessageOut } from '@/types/api'

const props = defineProps<{ shotId: number; canWrite: boolean }>()

// There is no push channel, so the chat asks for fresh messages itself,
// but only while the page is visible.
const POLL_INTERVAL_MS = 10_000
// Within this distance from the bottom the list follows new messages.
const STICK_TO_BOTTOM_PX = 80

const auth = useAuthStore()
const store = useChatStore()
const message = useMessage()
const dialog = useDialog()

const listRef = ref<HTMLElement | null>(null)
const draft = ref('')
const isSending = ref(false)
const editingId = ref<number | null>(null)
const editDraft = ref('')
const replyingTo = ref<MessageOut | null>(null)
const isSavingEdit = ref(false)

const visibility = useDocumentVisibility()
const currentUserId = computed(() => auth.currentUser?.id ?? null)
let followBottom = true

function scrollToBottom() {
  const list = listRef.value
  if (list) list.scrollTop = list.scrollHeight
}

function handleScroll() {
  const list = listRef.value
  if (!list) return
  followBottom = list.scrollHeight - list.scrollTop - list.clientHeight < STICK_TO_BOTTOM_PX
}

async function refresh() {
  try {
    await store.refresh()
  } catch {
    // A missed poll is harmless; the next one retries.
  }
}

watch(
  () => props.shotId,
  async (shotId) => {
    followBottom = true
    editingId.value = null
    replyingTo.value = null
    draft.value = ''
    try {
      await store.open(shotId)
    } catch {
      message.error('Не удалось загрузить чат.')
    }
  },
  { immediate: true },
)

useIntervalFn(() => {
  if (visibility.value === 'visible') refresh()
}, POLL_INTERVAL_MS)

watch(visibility, (state) => {
  if (state === 'visible') refresh()
})

// Follow new messages while the reader is at the bottom; leave the
// scroll position alone when they are reading history.
watch(
  () => store.items.at(-1)?.id,
  async () => {
    if (!followBottom) return
    await nextTick()
    scrollToBottom()
  },
  { flush: 'post' },
)

async function showOlder() {
  const list = listRef.value
  const heightBefore = list?.scrollHeight ?? 0
  try {
    await store.loadOlder()
  } catch {
    message.error('Не удалось загрузить более ранние сообщения.')
    return
  }
  // Keep what the reader was looking at in place.
  await nextTick()
  if (list) list.scrollTop += list.scrollHeight - heightBefore
}

function describeSendError(error: unknown, fallback: string): string {
  const detail = firstValidationMessage(error)
  if (detail?.includes('too long')) return 'Сообщение слишком длинное.'
  if (detail?.includes("can't be replied to")) {
    // The quoted message is gone (deleted meanwhile): drop the reply, keep the text.
    replyingTo.value = null
    return 'Сообщение, на которое вы отвечаете, больше недоступно.'
  }
  return fallback
}

async function handleSend() {
  const text = draft.value.trim()
  if (!text || isSending.value) return
  isSending.value = true
  try {
    await store.send(text, replyingTo.value?.id ?? null)
    draft.value = ''
    replyingTo.value = null
    followBottom = true
  } catch (error) {
    message.error(describeSendError(error, 'Не удалось отправить сообщение.'))
  } finally {
    isSending.value = false
  }
}

function handleDraftKeydown(event: KeyboardEvent) {
  // Enter sends, Shift+Enter adds a line (and IME composition is left alone).
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    handleSend()
  }
}

function iReacted(target: MessageOut, emoji: string): boolean {
  const reaction = target.reactions.find((item) => item.emoji === emoji)
  return (
    !!reaction && currentUserId.value !== null && reaction.user_ids.includes(currentUserId.value)
  )
}

async function toggleReaction(target: MessageOut, emoji: string) {
  try {
    await store.react(target.id, emoji, !iReacted(target, emoji))
  } catch {
    message.error('Не удалось изменить реакцию.')
  }
}

function startReply(target: MessageOut) {
  replyingTo.value = target
}

function quoteText(target: MessageOut): string {
  const quote = target.text.replace(/\s+/g, ' ')
  return quote.length > 100 ? `${quote.slice(0, 100)}…` : quote
}

function startEdit(target: MessageOut) {
  editingId.value = target.id
  editDraft.value = target.text
}

async function saveEdit() {
  const id = editingId.value
  const text = editDraft.value.trim()
  if (id === null || !text) return
  isSavingEdit.value = true
  try {
    await store.edit(id, text)
    editingId.value = null
  } catch (error) {
    message.error(describeSendError(error, 'Не удалось сохранить сообщение.'))
  } finally {
    isSavingEdit.value = false
  }
}

function confirmDelete(target: MessageOut) {
  dialog.warning({
    title: 'Удалить сообщение',
    content: 'Удалить сообщение? Это действие необратимо.',
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.remove(target.id)
      } catch {
        message.error('Не удалось удалить сообщение.')
      }
    },
  })
}

function isOwn(target: MessageOut): boolean {
  return target.type === 'user' && target.created_by?.id === currentUserId.value
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' })
}
</script>

<template>
  <div class="shot-chat">
    <div ref="listRef" class="shot-chat__list" @scroll="handleScroll">
      <div v-if="store.hasOlder" class="shot-chat__older">
        <n-button size="small" quaternary :loading="store.isLoadingOlder" @click="showOlder">
          Показать более ранние
        </n-button>
      </div>

      <p v-if="!store.isLoading && store.items.length === 0" class="shot-chat__empty">
        Сообщений пока нет.
      </p>

      <template v-for="item in store.items" :key="item.id">
        <div v-if="item.type === 'system'" class="shot-chat__system-block">
          <p class="shot-chat__system">
            {{ describeSystemMessage(item) }}
            <span class="shot-chat__time">{{ formatTime(item.created_at) }}</span>
          </p>
          <chat-reactions
            :reactions="item.reactions"
            :current-user-id="currentUserId"
            :can-react="canWrite"
            @toggle="toggleReaction(item, $event)"
          />
        </div>

        <div v-else class="shot-chat__message">
          <div class="shot-chat__meta">
            <strong>{{ userName(item.created_by) }}</strong>
            <span class="shot-chat__time">{{ formatTime(item.created_at) }}</span>
            <span v-if="item.edited_at" class="shot-chat__time">(изменено)</span>
            <span v-if="canWrite && editingId !== item.id" class="shot-chat__actions">
              <n-button size="tiny" quaternary @click="startReply(item)">Ответить</n-button>
              <template v-if="isOwn(item)">
                <n-button size="tiny" quaternary @click="startEdit(item)">Изменить</n-button>
                <n-button size="tiny" quaternary type="error" @click="confirmDelete(item)">
                  Удалить
                </n-button>
              </template>
            </span>
          </div>

          <div v-if="item.reply_to" class="shot-chat__quote">
            <strong>{{ userName(item.reply_to.author) }}</strong>
            <span v-if="item.reply_to.deleted" class="shot-chat__deleted">Сообщение удалено</span>
            <span v-else>{{ item.reply_to.text }}</span>
          </div>

          <div v-if="editingId === item.id" class="shot-chat__edit">
            <n-input
              v-model:value="editDraft"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 6 }"
            />
            <div class="shot-chat__edit-actions">
              <n-button size="small" :disabled="isSavingEdit" @click="editingId = null">
                Отмена
              </n-button>
              <n-button
                size="small"
                type="primary"
                :disabled="!editDraft.trim()"
                :loading="isSavingEdit"
                @click="saveEdit"
              >
                Сохранить
              </n-button>
            </div>
          </div>
          <p v-else class="shot-chat__text">{{ item.text }}</p>
          <chat-reactions
            :reactions="item.reactions"
            :current-user-id="currentUserId"
            :can-react="canWrite"
            @toggle="toggleReaction(item, $event)"
          />
        </div>
      </template>
    </div>

    <div v-if="canWrite" class="shot-chat__composer-block">
      <div v-if="replyingTo" class="shot-chat__reply-bar">
        <span class="shot-chat__reply-text">
          Ответ для <strong>{{ userName(replyingTo.created_by) }}</strong
          >: {{ quoteText(replyingTo) }}
        </span>
        <n-button size="tiny" quaternary aria-label="Отменить ответ" @click="replyingTo = null">
          ✕
        </n-button>
      </div>
      <div class="shot-chat__composer">
        <n-input
          v-model:value="draft"
          type="textarea"
          placeholder="Сообщение (Enter — отправить, Shift+Enter — новая строка)"
          :autosize="{ minRows: 1, maxRows: 6 }"
          @keydown="handleDraftKeydown"
        />
        <n-button type="primary" :disabled="!draft.trim()" :loading="isSending" @click="handleSend">
          Отправить
        </n-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.shot-chat {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.shot-chat__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-height: 480px;
  overflow-y: auto;
  padding-right: var(--space-2);
}

.shot-chat__older {
  display: flex;
  justify-content: center;
}

.shot-chat__empty,
.shot-chat__system {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.shot-chat__system {
  text-align: center;
}

.shot-chat__message {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.shot-chat__meta {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.shot-chat__time {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.shot-chat__actions {
  margin-left: auto;
}

.shot-chat__text {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.shot-chat__edit {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.shot-chat__edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.shot-chat__system-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.shot-chat__quote {
  display: flex;
  flex-direction: column;
  padding: 2px var(--space-2);
  border-left: 3px solid var(--color-border, rgba(128, 128, 128, 0.5));
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
  overflow-wrap: anywhere;
}

.shot-chat__deleted {
  font-style: italic;
}

.shot-chat__composer-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.shot-chat__reply-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: 2px var(--space-2);
  border-left: 3px solid var(--color-accent, #3366ff);
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.shot-chat__reply-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shot-chat__composer {
  display: flex;
  align-items: flex-end;
  gap: var(--space-2);
}
</style>
