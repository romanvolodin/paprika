<script setup>
import { useDark, useToggle } from '@vueuse/core'

const isDark = useDark()
const toggleDark = useToggle(isDark)
</script>

<template>
  <div @click="toggleDark()" class="theme-toggler">
    {{ isDark ? '🌙' : '☀️' }}
  </div>
</template>

<style>
.theme-toggler {
  display: flex;
  justify-content: start;
  align-items: center;
  cursor: pointer;
  border: 2px solid #d5d5d5;
  border-radius: 50vh;
  padding: 0 2px;
  padding-bottom: 1px;
  width: 48px;
  height: 28px;
}
html.dark .theme-toggler {
  justify-content: end;
}
</style>
