<script setup>
import MessagesArea from './MessagesArea.vue';
import MessageInput from './MessageInput.vue';

defineProps({
  chatData: {
    type: Array,
    required: true
  },
  allUsers: {
    type: Array,
    required: true
  }
});
</script>

<template>
  <div class="chat-area">
    <MessagesArea :messages="chatData" :all-users="allUsers" />
    <MessageInput />
  </div>
</template>

<style scoped>
.chat-area {
  display: flex;
  flex-direction: column;
  background-color: burlywood;
  width: 100%;
  min-width: 200px;
  height: 900px;
}
</style>
