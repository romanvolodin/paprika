<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NPopover } from 'naive-ui'
import type { ReactionSummaryOut } from '@/types/api'

const props = defineProps<{
  reactions: ReactionSummaryOut[]
  currentUserId: number | null
  canReact: boolean
}>()

const emit = defineEmits<{ toggle: [emoji: string] }>()

// A small fixed palette; the backend accepts any emoji.
const PALETTE = ['👍', '❤️', '😂', '🎉', '👀', '🙏', '✅', '🔥']

const isPickerOpen = ref(false)

const chips = computed(() =>
  props.reactions.map((reaction) => ({
    emoji: reaction.emoji,
    count: reaction.user_ids.length,
    mine: props.currentUserId !== null && reaction.user_ids.includes(props.currentUserId),
  })),
)

function pick(emoji: string) {
  isPickerOpen.value = false
  emit('toggle', emoji)
}
</script>

<template>
  <div v-if="chips.length > 0 || canReact" class="chat-reactions">
    <button
      v-for="chip in chips"
      :key="chip.emoji"
      type="button"
      class="chat-reactions__chip"
      :class="{ 'chat-reactions__chip--mine': chip.mine }"
      :disabled="!canReact"
      @click="emit('toggle', chip.emoji)"
    >
      <span>{{ chip.emoji }}</span>
      <span class="chat-reactions__count">{{ chip.count }}</span>
    </button>

    <n-popover
      v-if="canReact"
      :show="isPickerOpen"
      trigger="manual"
      placement="top"
      @clickoutside="isPickerOpen = false"
    >
      <template #trigger>
        <n-button
          size="tiny"
          quaternary
          class="chat-reactions__add"
          aria-label="Добавить реакцию"
          @click="isPickerOpen = !isPickerOpen"
        >
          +
        </n-button>
      </template>
      <div class="chat-reactions__palette">
        <button
          v-for="emoji in PALETTE"
          :key="emoji"
          type="button"
          class="chat-reactions__pick"
          @click="pick(emoji)"
        >
          {{ emoji }}
        </button>
      </div>
    </n-popover>
  </div>
</template>

<style scoped>
.chat-reactions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1, 4px);
}

.chat-reactions__chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  height: 22px;
  border: 1px solid var(--color-border, rgba(128, 128, 128, 0.4));
  border-radius: 11px;
  background: none;
  color: inherit;
  font-size: var(--text-sm, 13px);
  cursor: pointer;
}

.chat-reactions__chip:disabled {
  cursor: default;
}

.chat-reactions__chip--mine {
  border-color: var(--color-accent, #3366ff);
  background: var(--color-accent-soft, rgba(51, 102, 255, 0.12));
}

.chat-reactions__count {
  color: var(--color-text-secondary);
}

.chat-reactions__palette {
  display: flex;
  gap: var(--space-1, 4px);
}

.chat-reactions__pick {
  padding: 2px 4px;
  border: none;
  border-radius: 4px;
  background: none;
  font-size: 18px;
  cursor: pointer;
}

.chat-reactions__pick:hover {
  background: var(--color-surface-muted, rgba(128, 128, 128, 0.15));
}
</style>
