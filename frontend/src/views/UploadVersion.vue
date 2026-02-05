<template>
  <div v-if="isLoading" class="loading">Загрузка...</div>
  <div v-else-if="error" class="error">{{ error }}</div>
  <div v-else class="upload-version">
    <div class="file-preview-section">
      <div v-if="!selectedFile" class="file-upload-area" @dragover.prevent @drop.prevent="handleFileDrop">
        <input type="file" ref="fileInput" @change="handleFileSelect" style="display: none" />
        <button @click="$refs.fileInput.click()" class="upload-button">Выбрать файл</button>
        <p>или перетащите файл сюда</p>
      </div>
      <div v-else class="file-preview">
        <img v-if="isImageFile(selectedFile)" :src="filePreviewUrl" alt="Предпросмотр" class="preview-image" />
        <video v-else-if="isVideoFile(selectedFile)" :src="filePreviewUrl" controls class="preview-video"></video>
        <div v-else class="file-info">
          <p>Имя файла: {{ selectedFile.name }}</p>
          <p>Размер: {{ formatFileSize(selectedFile.size) }}</p>
          <p>Тип: {{ selectedFile.type }}</p>
        </div>
        <button @click="removeFile" class="remove-file-button">Удалить файл</button>
      </div>
    </div>

    <div class="tasks-section">
      <h2>Задачи</h2>

      <div v-if="shotTasks.length === 0" class="no-tasks">Нет задач для отображения</div>
      <div v-else class="tasks-list">
        <div v-for="shotTask in shotTasks" :key="shotTask.id" class="task-item">
          <div class="task-description">{{ shotTask.task.description }}</div>
          <StatusDropdown
            v-model="shotTask.status"
            :statuses="statuses"
            @update:modelValue="onTaskStatusChange(shotTask)"
          />
          <label>Часы: <input class="hours-input" v-model="shotTask.hours" /></label>
        </div>
      </div>
    </div>

    <div class="comment-section">
      <h2>Комментарий</h2>
      <textarea v-model="comment" placeholder="Введите комментарий к версии..." class="comment-textarea"></textarea>
    </div>

    <div class="submit-section">
      <button @click="submitVersion" :disabled="isSubmitting" class="submit-button">
        {{ isSubmitting ? 'Отправка...' : 'Отправить версию' }}
      </button>
      <div v-if="submitError" class="submit-error">{{ submitError }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from '@/config/axiosConfig'
import router from '@/router'
import StatusDropdown from '@/components/StatusDropdown.vue'

const route = useRoute()
const projectCode = route.params.projectCode
const shotName = route.params.shotName

const isLoading = ref(true)
const error = ref(null)
const isSubmitting = ref(false)
const submitError = ref(null)

const selectedFile = ref(null)
const filePreviewUrl = ref('')
const shotTasks = ref([])
const statuses = ref([])
const comment = ref('')

const fileInput = ref(null)

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    selectedFile.value = file
    createFilePreview(file)
  }
}

const handleFileDrop = (event) => {
  const file = event.dataTransfer.files[0]
  if (file) {
    selectedFile.value = file
    createFilePreview(file)
  }
}

const createFilePreview = (file) => {
  if (filePreviewUrl.value) {
    URL.revokeObjectURL(filePreviewUrl.value)
  }

  if (isImageFile(file) || isVideoFile(file)) {
    filePreviewUrl.value = URL.createObjectURL(file)
  } else {
    filePreviewUrl.value = ''
  }
}

const removeFile = () => {
  if (filePreviewUrl.value) {
    URL.revokeObjectURL(filePreviewUrl.value)
  }
  selectedFile.value = null
  filePreviewUrl.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const isImageFile = (file) => {
  return file.type.startsWith('image/')
}

const isVideoFile = (file) => {
  return file.type.startsWith('video/')
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const fetchShotTasks = async () => {
  try {
    const response = await axios.get(`/api/projects/${projectCode}/shots/${shotName}/tasks`)
    shotTasks.value = response.data.map(shotTask => ({
      id: shotTask.id,
      task: {
        id: shotTask.task.id,
        description: shotTask.task.description
      },
      status: shotTask.status.id,
      hours: shotTask.hours
    }))

  } catch (err) {
    error.value = 'Ошибка при загрузке задач шота'
    console.error(err)
  }
}

const fetchStatuses = async () => {
  try {
    const response = await axios.get('/api/statuses/')
    statuses.value = response.data.results
  } catch (err) {
    error.value = 'Ошибка при загрузке статусов'
    console.error(err)
  }
}

const onTaskStatusChange = (task) => {
  // Локальное обновление статуса задачи
  // Отправка на сервер произойдет при сабмите формы
}

const submitVersion = async () => {
  if (!selectedFile.value) {
    submitError.value = 'Пожалуйста, выберите файл для загрузки'
    return
  }

  isSubmitting.value = true
  submitError.value = null

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    // Добавляем комментарий, если он есть
    if (comment.value) {
      formData.append('comment', comment.value)
    }

    const taskUpdates = shotTasks.value
      .map(shotTask => ({
        task_id: shotTask.id,
        status_id: shotTask.status,
        hours: shotTask.hours
      }))

    if (taskUpdates.length > 0) {
      formData.append('task_updates', JSON.stringify(taskUpdates))
    }

    await axios.post(`/api/projects/${projectCode}/shots/${shotName}/versions/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    router.push({ name: 'shot-details', params: { projectCode, shotName } })
  } catch (err) {
    submitError.value = 'Ошибка при отправке версии: ' + (err.response?.data?.detail || err.message)
    console.error(err)
  } finally {
    isSubmitting.value = false
  }
}

// Инициализация
onMounted(async () => {
  try {
    await Promise.all([
      fetchShotTasks(),
      fetchStatuses()
    ])
  } catch (err) {
    error.value = 'Ошибка при загрузке данных'
    console.error(err)
  } finally {
    isLoading.value = false
  }
})
</script>

<style scoped>
.upload-version {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.loading, .error {
  text-align: center;
  padding: 20px;
}

.error {
  color: #d32f2f;
  background-color: #ffebee;
  border: 1px solid #ffcdd2;
  border-radius: 4px;
}

.file-preview-section {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px dashed #ccc;
  border-radius: 4px;
  text-align: center;
}

.file-upload-area {
  padding: 40px 20px;
}

.upload-button {
  background-color: #1976d2;
  color: white;
  border: none;
  padding: 10px 20px;
  font-size: 16px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 10px;
}

.upload-button:hover {
  background-color: #1565c0;
}

.file-preview {
  position: relative;
}

.preview-image, .preview-video {
  max-width: 100%;
  max-height: 400px;
  display: block;
  margin: 0 auto;
}

.file-info {
  text-align: left;
  margin: 20px 0;
}

.remove-file-button {
  background-color: #f44336;
  color: white;
  border: none;
  padding: 10px 20px;
  font-size: 14px;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 10px;
}

.remove-file-button:hover {
  background-color: #d32f2f;
}

.tasks-section {
  margin-bottom: 30px;
}

.tasks-section h2 {
  margin-bottom: 15px;
}

.no-tasks {
  text-align: center;
  color: #666;
  padding: 20px;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.task-description {
  flex: 1;
}

.status-select {
  padding: 5px;
  border-radius: 4px;
  border: 1px solid #ccc;
}

.status-color {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid #ccc;
}

.comment-section {
  margin-bottom: 30px;
}

.comment-section h2 {
  margin-bottom: 15px;
}

.comment-textarea {
  width: 100%;
  min-height: 100px;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-family: inherit;
  resize: vertical;
}

.submit-section {
  text-align: center;
}

.submit-button {
  background-color: #4caf50;
  color: white;
  border: none;
  padding: 12px 24px;
  font-size: 16px;
  border-radius: 4px;
  cursor: pointer;
}

.submit-button:hover:not(:disabled) {
  background-color: #388e3c;
}

.submit-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.submit-error {
  color: #d32f2f;
  margin-top: 10px;
}

.hours-input {
  width: 40px;
  padding: 3px;
  border-radius: 4px;
  background-color: #666;
  color: white;
}
</style>
