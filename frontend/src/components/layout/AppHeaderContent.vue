<script setup lang="ts">
import { appHeaderSlot } from '@/composables/useAppHeaderSlot'
</script>

<template>
  <Teleport :to="appHeaderSlot" :disabled="!appHeaderSlot">
    <slot />
  </Teleport>
</template>
