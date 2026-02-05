<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import MessageBubble from './MessageBubble.vue'

import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
})

const _chatArea = ref(null)

const props = defineProps({
  messages: {
    type: Array,
    required: true
  },
  allUsers: {
    type: Array,
    required: true
  }
});

function scrollToLastMessage() {
  if (_chatArea.value) {
    _chatArea.value.scrollTo({
      top: _chatArea.value.scrollHeight,
      behavior: 'auto',
    })
  }
}

watch(props.messages, () => {
  nextTick(scrollToLastMessage)
})


const getAuthorById = (id) => {
  return props.allUsers.find((user) => {
    return user.id === id
  })
}

function formatAuthorName(authorId) {
  if (!authorId) {
    return ''
  }

  const author = getAuthorById(authorId)
  return `${author.first_name} ${author.last_name}`
}

function formatDateTime(datetime) {
  return new Date(datetime).toLocaleString('ru-ru', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: 'numeric',
  })
}

onMounted(() => {
  scrollToLastMessage()
})
</script>

<template>
  <div class="messages-area">
    <div v-if="messages.length === 0" class="empty">
      Сообщений пока нет
    </div>

    <div v-else class="chat-area" ref="_chatArea">
      <div class="messages">
        <MessageBubble
          v-for="message in messages"
          :key="message.created_at"
          :author="formatAuthorName(message.created_by)"
          :body="md.render(message.text)"
          :datetime="formatDateTime(message.created_at)"
          :attachments="message.attachments"
          :reply-to-author="formatAuthorName(message.reply_to_display?.created_by)"
          :reply-to-text="message.reply_to_display?.text"
          @reply="console.log(message)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.messages-area {
  background-color: gold;
  flex-grow: 1;
  overflow-y: scroll;
}
.empty {
  display: flex;
  flex-grow: 1;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 20px;
}
.chat-area {
  flex-grow: 1;
  overflow-y: auto;
  overflow-x: hidden;
}
.messages {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
}
</style>
