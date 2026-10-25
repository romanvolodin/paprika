<script setup lang="ts">
import { NTag } from 'naive-ui'
import { tagColor } from '@/utils/color'
import type { ShotStatusOut } from '@/types/api'

defineProps<{ status: ShotStatusOut }>()
</script>

<template>
  <n-tag size="small" round :color="tagColor(status.color)">{{ status.name }}</n-tag>
</template>
