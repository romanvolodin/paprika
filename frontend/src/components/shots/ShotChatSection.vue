<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useDocumentVisibility, useIntervalFn } from '@vueuse/core'
import { NButton, NIcon, NInput, NSelect, useDialog, useMessage } from 'naive-ui'
import { AttachOutline, CloseOutline, FilmOutline } from '@vicons/ionicons5'
import * as versionsApi from '@/api/versions'
import ChatMessageFiles from '@/components/shots/ChatMessageFiles.vue'
import ChatReactions from '@/components/shots/ChatReactions.vue'
import { MAX_CHAT_ATTACHMENTS, useChatAttachments } from '@/composables/useChatAttachments'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { describeSystemMessage, userName } from '@/utils/chat'
import { formatFileSize } from '@/utils/format'
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

const attachments = useChatAttachments(() => props.shotId)
const fileInput = ref<HTMLInputElement | null>(null)

// Versions of the shot that the next message can point at. The list is
// fetched the first time the picker is opened.
const isPickingVersions = ref(false)
const versionOptions = ref<Array<{ label: string; value: number }>>([])
const selectedVersionIds = ref<number[]>([])
const isLoadingVersions = ref(false)
let versionsLoadedFor: number | null = null

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
    selectedVersionIds.value = []
    isPickingVersions.value = false
    versionOptions.value = []
    versionsLoadedFor = null
    void attachments.discardAll()
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

const canSend = computed(
  () =>
    (draft.value.trim() !== '' ||
      attachments.readyIds.value.length > 0 ||
      selectedVersionIds.value.length > 0) &&
    !attachments.isUploading.value &&
    !isSending.value,
)

async function handleSend() {
  if (!canSend.value) return
  isSending.value = true
  try {
    await store.send(draft.value.trim(), {
      replyToId: replyingTo.value?.id ?? null,
      versionIds: selectedVersionIds.value,
      attachmentIds: attachments.readyIds.value,
    })
    draft.value = ''
    replyingTo.value = null
    selectedVersionIds.value = []
    isPickingVersions.value = false
    attachments.clear()
    followBottom = true
  } catch (error) {
    message.error(describeSendError(error, 'Не удалось отправить сообщение.'))
  } finally {
    isSending.value = false
  }
}

function pickFiles() {
  fileInput.value?.click()
}

function handleFilesChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const chosen = [...(input.files ?? [])]
  // Reset so choosing the same file again still fires.
  input.value = ''
  const skipped = attachments.add(chosen)
  if (skipped > 0) {
    message.warning(`В одном сообщении не больше ${MAX_CHAT_ATTACHMENTS} файлов.`)
  }
}

async function toggleVersionPicker() {
  isPickingVersions.value = !isPickingVersions.value
  if (!isPickingVersions.value || versionsLoadedFor === props.shotId) return
  const shotId = props.shotId
  isLoadingVersions.value = true
  try {
    const result = await versionsApi.listVersions(shotId, { page_size: 100 })
    // The reader may have moved to another shot while this was loading.
    if (shotId !== props.shotId) return
    versionOptions.value = result.items.map((version) => ({
      label: version.name,
      value: version.id,
    }))
    versionsLoadedFor = shotId
  } catch {
    message.error('Не удалось загрузить версии кадра.')
    isPickingVersions.value = false
  } finally {
    isLoadingVersions.value = false
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

function hasExtras(target: MessageOut): boolean {
  return target.attachments.length > 0 || target.versions.length > 0
}

function canSaveEdit(target: MessageOut): boolean {
  return editDraft.value.trim() !== '' || hasExtras(target)
}

async function saveEdit(target: MessageOut) {
  const text = editDraft.value.trim()
  if (!canSaveEdit(target)) return
  isSavingEdit.value = true
  try {
    await store.edit(target.id, text)
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
                :disabled="!canSaveEdit(item)"
                :loading="isSavingEdit"
                @click="saveEdit(item)"
              >
                Сохранить
              </n-button>
            </div>
          </div>
          <p v-else-if="item.text" class="shot-chat__text">{{ item.text }}</p>
          <chat-message-files :attachments="item.attachments" :versions="item.versions" />
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
      <div v-if="attachments.files.value.length > 0" class="shot-chat__chips">
        <span
          v-for="file in attachments.files.value"
          :key="file.key"
          class="shot-chat__chip"
          :class="{ 'shot-chat__chip--failed': file.status === 'failed' }"
        >
          <span class="shot-chat__chip-name">{{ file.name }}</span>
          <span class="shot-chat__chip-meta">
            <template v-if="file.status === 'uploading'">{{ file.progress }}%</template>
            <template v-else-if="file.status === 'failed'">{{ file.error }}</template>
            <template v-else>{{ formatFileSize(file.size) }}</template>
          </span>
          <button
            type="button"
            class="shot-chat__chip-remove"
            :aria-label="`Убрать ${file.name}`"
            @click="attachments.remove(file.key)"
          >
            <n-icon :component="CloseOutline" />
          </button>
        </span>
      </div>
      <n-select
        v-if="isPickingVersions"
        v-model:value="selectedVersionIds"
        multiple
        filterable
        clearable
        placeholder="Версии кадра"
        :options="versionOptions"
        :loading="isLoadingVersions"
      />
      <div class="shot-chat__composer">
        <input
          ref="fileInput"
          class="shot-chat__file-input"
          type="file"
          multiple
          @change="handleFilesChosen"
        />
        <n-button quaternary aria-label="Прикрепить файл" @click="pickFiles">
          <template #icon><n-icon :component="AttachOutline" /></template>
        </n-button>
        <n-button
          quaternary
          aria-label="Приложить версию"
          :type="isPickingVersions || selectedVersionIds.length > 0 ? 'primary' : 'default'"
          @click="toggleVersionPicker"
        >
          <template #icon><n-icon :component="FilmOutline" /></template>
        </n-button>
        <n-input
          v-model:value="draft"
          type="textarea"
          placeholder="Сообщение (Enter — отправить, Shift+Enter — новая строка)"
          :autosize="{ minRows: 1, maxRows: 6 }"
          @keydown="handleDraftKeydown"
        />
        <n-button type="primary" :disabled="!canSend" :loading="isSending" @click="handleSend">
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

.shot-chat__file-input {
  display: none;
}

.shot-chat__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.shot-chat__chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  max-width: 100%;
  padding: 2px var(--space-2);
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.4));
  border-radius: 12px;
  font-size: var(--text-sm, 13px);
}

.shot-chat__chip--failed {
  border-color: var(--color-error, #d03050);
}

.shot-chat__chip-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 220px;
}

.shot-chat__chip-meta {
  color: var(--color-text-secondary);
}

.shot-chat__chip--failed .shot-chat__chip-meta {
  color: var(--color-error, #d03050);
}

.shot-chat__chip-remove {
  display: inline-flex;
  padding: 0;
  border: none;
  background: none;
  color: inherit;
  cursor: pointer;
}

.shot-chat__composer {
  display: flex;
  align-items: flex-end;
  gap: var(--space-2);
}
</style>
