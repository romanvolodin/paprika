<script setup>
defineProps({
  user: {
    type: Object,
    default: null,
  },
})
</script>

<template>
  <span v-if="!user" class="feed-user-unknown">Неизвестно</span>
  <span v-else class="feed-user-badge">
    <img
      v-if="user.avatar"
      class="feed-user-avatar"
      :src="user.avatar"
      alt=""
    />
    <span
      v-else
      class="feed-user-avatar feed-user-avatar--placeholder"
    >{{ (user.first_name || user.email || '?')[0].toUpperCase() }}</span>
    <span class="feed-user-name">{{ user.first_name || user.email || 'Неизвестно' }}</span>
  </span>
</template>

<style scoped>
.feed-user-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
  flex-shrink: 0;
}

.feed-user-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  margin-bottom: 2px;
}

.feed-user-avatar--placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: #6c757d;
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  line-height: 1;
}

.feed-user-name {
  font-weight: 600;
}

.feed-user-unknown {
  font-weight: 600;
  color: #6c757d;
}
</style>
