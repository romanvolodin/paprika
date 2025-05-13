<script setup>
import { useAuthStore } from '@/stores/auth'
import { onMounted, ref } from 'vue'

const auth = useAuthStore()
const _user = ref({})

onMounted(() => {
  _user.value = auth.user
})
</script>

<template>
  <header>
    <div class="user" v-if="_user">
      <p class="name">{{ _user.first_name || _user.email }}</p>
      <img class="avatar" :src="_user.avatar" alt="" />
    </div>
  </header>
</template>

<style scoped>
header {
  display: flex;
  justify-content: end;
  box-shadow: 0px 10px 10px #00000008;
  padding: 10px;
}
.user {
  display: flex;
  align-items: center;
}
.name {
  margin-right: 10px;
}
.avatar {
  border-radius: 50vh;
  aspect-ratio: 1;
  width: 40px;
  object-fit: cover;
}
</style>
