<script setup lang="ts">
import { computed } from 'vue'
import { NAvatar } from 'naive-ui'
import type { UserOut } from '@/types/api'

const props = withDefaults(
  defineProps<{
    user: Pick<UserOut, 'first_name' | 'last_name' | 'email' | 'avatar'> | null
    size?: number
  }>(),
  { size: 28 },
)

// "?" for a deleted user, the e-mail's first letter for one without a name.
const initials = computed(() => {
  const user = props.user
  if (!user) return '?'
  const letters = `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`.trim()
  return (letters || user.email.charAt(0)).toUpperCase()
})
</script>

<template>
  <!-- naive-ui does not draw the picture when the avatar has any default
       slot content, so the initials are a separate element. -->
  <n-avatar v-if="user?.avatar" round :size="size" :src="user.avatar" />
  <n-avatar v-else round :size="size" class="user-avatar__initials">{{ initials }}</n-avatar>
</template>

<style scoped>
.user-avatar__initials {
  font-family: var(--font-mono);
  font-size: 11px;
}
</style>
