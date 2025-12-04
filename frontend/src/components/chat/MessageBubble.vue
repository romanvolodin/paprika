<script setup>
defineProps({
  author: String,
  body: String,
  datetime: String,
  attachments: Array,
  replyToAuthor: String,
  replyToText: String,
})
</script>

<template>
  <div class="message">
    <div class="message-header">
      <p class="author">
        {{ author }}
      </p>
      <span class="reply" @click="$emit('reply')">Ответить</span>
    </div>

    <blockquote class="quote" v-if="replyToAuthor && replyToText">
      <p>{{ replyToAuthor }}</p>
      <p>{{ replyToText }}</p>
    </blockquote>

    <div v-if="attachments" class="attachments-wrapper">
      <div v-for="attachment in attachments" :key="attachment" class="attachment">
        <a :href="attachment.file" target="_blank">
          <img :src="attachment.file" />
        </a>
      </div>
    </div>

    <div class="markdown-body" v-html="body"></div>
    <p class="date-time">{{ datetime }}</p>
  </div>
</template>

<style scoped>
.message {
  border-radius: 10px;
  border-bottom-left-radius: 0;
  background-color: hsl(83, 10%, 92%);
  padding: 10px;
}
html.dark .message {
  background-color: #444;
}
.message-header {
  display: flex;
  justify-content: space-between;
}
.reply {
  display: none;
  opacity: 0.4;
  cursor: pointer;
}
.message:hover .reply {
  display: inline;
}
.author {
  font-weight: bold;
}
.quote {
  margin: 5px 0;
  border-left: 4px solid hsl(83, 35%, 50%);
  border-radius: 5px;
  background-color: hsl(83, 15%, 80%);
  padding: 3px 6px;
}
html.dark .quote {
  border-left: 4px solid #6e8a40;
  background-color: #686c60;
}
.markdown-body :deep(p) {
  word-wrap: break-word;
}
.markdown-body :deep(p:not(:last-child)) {
  margin-bottom: 18px;
}
.markdown-body :deep(a) {
  color: #6e8a40;
}
.date-time {
  opacity: 0.4;
  text-align: right;
}
.attachments-wrapper {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 3px;
  margin: 5px 0;
  max-width: 600px;
}
.attachment {
  border-radius: 5px;
  aspect-ratio: 1;
  overflow: hidden;
}
.attachment img {
  filter: brightness(0.75);
  aspect-ratio: 1;
  width: 100%;
  object-fit: cover;
}
.attachment img:hover {
  filter: brightness(1);
}
</style>
