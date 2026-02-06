<script setup>
import { useTextareaAutosize } from '@vueuse/core'

const { textarea: userMessageTextarea, input: _message } = useTextareaAutosize()

const emit = defineEmits(['sendMessage']);

function handleSendMessage() {
  emit('sendMessage', _message.value);
}
</script>

<template>
  <form
    @submit.prevent="handleSendMessage"
    class="message-input"
    enctype="multipart/form-data"
  >
    <div class="form-row">
      <label>
        <input
          type="file"
          id="uploading-attachments"
          @change="handleFileChange"
          multiple
          hidden
        />
        📎
      </label>
      <textarea
        class="textarea hide-scroll"
        ref="userMessageTextarea"
        v-model="_message"
        placeholder="Сообщение..."
        @input="replaceToMdash"
        @keydown.enter.exact="handleSendMessage"
      ></textarea>
      <button type="submit">➜</button>
    </div>
  </form>
</template>

<style scoped>
.message-input {
  background-color: tomato;
}
.form-row {
  display: flex;
  font-size: 18px;
  align-items: center;
}
.form-row > label,
.form-row > button {
  width: 46px;
  height: 46px;
  padding: 5px;
  font-size: 24px;
  align-self: end;
}
.textarea {
  max-height: 400px;
  flex-grow: 1;
  padding: 10px 0;
}
.hide-scroll {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.hide-scroll::-webkit-scrollbar {
  display: none;
}
</style>
