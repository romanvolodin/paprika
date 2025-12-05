<script setup>
import { onMounted, ref } from 'vue'

const props = defineProps({
  projectCode: String,
  name: String,
  thumb: String,
  status: String,
  statusColor: String,
})

const cardElement = ref(null)

onMounted(() => {
  const lastViewedShot = localStorage.getItem('lastViewedShot')
  if (lastViewedShot && lastViewedShot === `${props.name}`) {
    cardElement.value.classList.add('highlight')
    localStorage.removeItem('lastViewedShot')
  }
})
</script>

<template>
  <div ref="cardElement" class="shot-card">
    <router-link
      :to="{
        name: 'shot-details',
        params: { projectCode: projectCode, shotName: name },
      }"
    >
      <span class="shot-status" :style="{ 'background-color': statusColor }">
        {{ status }}
      </span>

      <img v-if="thumb" :src="thumb" :alt="name" class="shot-image" />
      <div v-else class="shot-no-thumb">Нет превью</div>
      <div class="shot-info">
        {{ name }}
      </div>
    </router-link>
  </div>
</template>

<style scoped>
.shot-card {
  position: relative;
  transition: transform 0.1s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border: 2px solid transparent;
  overflow: hidden;
}
.shot-card.highlight {
  animation: highlightAnimation 2s ease-out;
}
@keyframes highlightAnimation {
  0% {
    border: 2px solid #ffd900ff;
  }
  50% {
    border: 2px solid #ffd900ff;
  }
  100% {
    border: 2px solid transparent;
  }
}
.shot-status {
  position: absolute;
  right: 0;
  margin: 5px;
  border-radius: 5px;
  padding: 2px 7px;
  color: #fff;
  font-size: 12px;
}
.shot-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
}
.shot-no-thumb {
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #ddd;
  width: 100%;
  height: 200px;
  color: #999;
}
html.dark .shot-no-thumb {
  background-color: black;
  color: #ccc;
}
.shot-info {
  padding: 2px 5px;
}
</style>
