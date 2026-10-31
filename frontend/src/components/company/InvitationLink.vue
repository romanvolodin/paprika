<script setup lang="ts">
import { computed, ref } from 'vue'
import { NButton, NIcon, NInput, useMessage } from 'naive-ui'
import { CopyOutline } from '@vicons/ionicons5'
import { copyToClipboard, invitationLink } from '@/utils/invitationLink'

const props = defineProps<{ token: string }>()

const message = useMessage()
const input = ref<InstanceType<typeof NInput> | null>(null)
const link = computed(() => invitationLink(props.token))

async function handleCopy() {
  if (await copyToClipboard(link.value)) {
    message.success('Ссылка скопирована.')
  } else {
    message.warning('Не удалось скопировать. Выделите ссылку и скопируйте вручную.')
  }
}
</script>

<template>
  <div class="invitation-link">
    <n-input
      ref="input"
      :value="link"
      readonly
      aria-label="Ссылка-приглашение"
      @focus="input?.select()"
    />
    <n-button @click="handleCopy">
      <template #icon><n-icon :component="CopyOutline" /></template>
      Копировать
    </n-button>
  </div>
</template>

<style scoped>
.invitation-link {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
</style>
