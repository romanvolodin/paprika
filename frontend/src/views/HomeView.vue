<script setup>
import { ref } from 'vue'

const message = ref('')

fetch('http://localhost:8000/api/')
  .then((response) => {
    response.json().then((data) => {
      message.value = data.message
    })
  })
  .catch((err) => {
    console.error(err)
  })
</script>

<template>
  message: {{ message }}
</template>
