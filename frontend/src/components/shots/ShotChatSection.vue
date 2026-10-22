<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useDocumentVisibility, useIntervalFn } from '@vueuse/core'
import { NButton, NDropdown, NIcon, NInput, NSelect, useDialog, useMessage } from 'naive-ui'
import {
  AttachOutline,
  CloseOutline,
  EllipsisHorizontalOutline,
  FilmOutline,
} from '@vicons/ionicons5'
import * as versionsApi from '@/api/versions'
import ChatMessageFiles from '@/components/shots/ChatMessageFiles.vue'
import ChatReactions from '@/components/shots/ChatReactions.vue'
import { MAX_CHAT_ATTACHMENTS, useChatAttachments } from '@/composables/useChatAttachments'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import UserAvatar from '@/components/common/UserAvatar.vue'
import { buildChatEntries, describeSystemMessage, formatClock, userName } from '@/utils/chat'
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
  // The menu is anchored to a point of the screen, it would be left behind.
  menu.value = null
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

const entries = computed(() => buildChatEntries(store.items))

// --- Menu of a message ---------------------------------------------------

// One menu for the whole feed, put where the right click or the "⋯"
// button was.
const menu = ref<{ message: MessageOut; x: number; y: number } | null>(null)

const menuOptions = computed(() => {
  const target = menu.value?.message
  if (!target) return []
  return [
    { label: 'Ответить', key: 'reply' },
    ...(isOwn(target)
      ? [
          { label: 'Изменить', key: 'edit' },
          {
            label: 'Удалить',
            key: 'delete',
            props: { style: 'color: var(--color-status-blocked)' },
          },
        ]
      : []),
  ]
})

function canOpenMenu(target: MessageOut): boolean {
  return props.canWrite && editingId.value !== target.id
}

function openContextMenu(target: MessageOut, event: MouseEvent) {
  if (!canOpenMenu(target)) return
  event.preventDefault()
  menu.value = { message: target, x: event.clientX, y: event.clientY }
}

function openMenuFromButton(target: MessageOut, event: MouseEvent) {
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  menu.value = { message: target, x: rect.left, y: rect.bottom }
}

function handleMenuSelect(key: string) {
  const target = menu.value?.message
  menu.value = null
  if (!target) return
  if (key === 'reply') startReply(target)
  else if (key === 'edit') startEdit(target)
  else if (key === 'delete') confirmDelete(target)
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

      <template
        v-for="{ message: item, dayLabel, firstOfRun, lastOfRun } in entries"
        :key="item.id"
      >
        <p v-if="dayLabel" class="shot-chat__day">{{ dayLabel }}</p>

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

        <div
          v-else
          class="shot-chat__message"
          :class="{
            'shot-chat__message--own': isOwn(item),
            'shot-chat__message--first': firstOfRun,
          }"
        >
          <div v-if="!isOwn(item)" class="shot-chat__avatar">
            <user-avatar v-if="lastOfRun" :user="item.created_by" :size="28" />
          </div>

          <div class="shot-chat__column">
            <div
              class="shot-chat__bubble"
              :class="{ 'shot-chat__bubble--tail': lastOfRun }"
              @contextmenu="openContextMenu(item, $event)"
            >
              <strong v-if="!isOwn(item) && firstOfRun" class="shot-chat__author">
                {{ userName(item.created_by) }}
              </strong>

              <div v-if="item.reply_to" class="shot-chat__quote">
                <strong>{{ userName(item.reply_to.author) }}</strong>
                <span v-if="item.reply_to.deleted" class="shot-chat__deleted">
                  Сообщение удалено
                </span>
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

              <span class="shot-chat__stamp">
                <span v-if="item.edited_at">(изменено)</span>
                {{ formatClock(item.created_at) }}
              </span>
            </div>

            <chat-reactions
              :reactions="item.reactions"
              :current-user-id="currentUserId"
              :can-react="canWrite"
              @toggle="toggleReaction(item, $event)"
            />
          </div>

          <button
            v-if="canOpenMenu(item)"
            type="button"
            class="shot-chat__more"
            aria-label="Действия с сообщением"
            @click="openMenuFromButton(item, $event)"
          >
            <n-icon :component="EllipsisHorizontalOutline" />
          </button>
        </div>
      </template>
    </div>

    <n-dropdown
      trigger="manual"
      placement="bottom-start"
      :show="menu !== null"
      :x="menu?.x ?? 0"
      :y="menu?.y ?? 0"
      :options="menuOptions"
      @select="handleMenuSelect"
      @clickoutside="menu = null"
    />

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
  height: 100%;
  min-height: 0;
}

.shot-chat__list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-height: 0;
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

.shot-chat__day {
  align-self: center;
  margin: var(--space-3) 0 var(--space-1);
  padding: 2px var(--space-3);
  border-radius: 999px;
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  font-size: 12px;
}

.shot-chat__time {
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.shot-chat__message {
  display: flex;
  align-items: flex-end;
  gap: var(--space-2);
}

.shot-chat__message--first {
  margin-top: var(--space-2);
}

.shot-chat__message--own {
  justify-content: flex-end;
}

.shot-chat__avatar {
  flex: none;
  width: 28px;
}

.shot-chat__column {
  display: flex;
  flex: 0 1 auto;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  max-width: 85%;
}

.shot-chat__message--own .shot-chat__column {
  align-items: flex-end;
}

.shot-chat__bubble {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-2) var(--space-3);
  border-radius: 12px;
  background: var(--color-bg-hover);
}

.shot-chat__message--own .shot-chat__bubble {
  background: var(--color-accent-soft);
}

.shot-chat__bubble--tail {
  border-bottom-left-radius: 4px;
}

.shot-chat__message--own .shot-chat__bubble--tail {
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 12px;
}

.shot-chat__author {
  color: var(--color-accent);
  font-size: var(--text-sm, 13px);
}

.shot-chat__stamp {
  align-self: flex-end;
  display: flex;
  gap: var(--space-1);
  color: var(--color-text-secondary);
  font-size: 11px;
}

.shot-chat__more {
  display: flex;
  flex: none;
  align-items: center;
  align-self: center;
  padding: var(--space-1);
  border: none;
  border-radius: 50%;
  background: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  opacity: 0;
}

.shot-chat__message--own .shot-chat__more {
  order: -1;
}

.shot-chat__message:hover .shot-chat__more,
.shot-chat__more:focus-visible {
  opacity: 1;
}

.shot-chat__more:hover {
  background: var(--color-bg-hover);
  color: var(--color-text);
}

/* No hovering on a touch screen: the button is always there. */
@media (hover: none) {
  .shot-chat__more {
    opacity: 1;
  }
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
  border-left: 3px solid var(--color-accent);
  border-radius: 2px;
  background: var(--color-accent-soft);
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
