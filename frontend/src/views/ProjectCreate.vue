<template>
  <div v-if="isLoading" class="loading">Загрузка...</div>
  <div v-else-if="error" class="error">{{ error }}</div>
  <div v-else class="create-project">
    <h1>Создать проект</h1>

    <div class="file-preview-section">
      <div v-if="!selectedFile" class="file-upload-area" @dragover.prevent @drop.prevent="handleFileDrop">
        <input type="file" ref="fileInput" @change="handleFileSelect" style="display: none" accept="image/*" />
        <button @click="$refs.fileInput.click()" class="upload-button">Выбрать изображение</button>
        <p>или перетащите файл сюда</p>
        <p class="file-hint">Поддерживаются изображения (JPG, PNG, GIF). Максимальный размер 5MB.</p>
      </div>
      <div v-else class="file-preview">
        <div class="selected-file-header">
          <h2 class="selected-file-name">{{ selectedFile.name }}</h2>
          <button @click="removeFile" class="remove-file-button">𐄂</button>
        </div>
        <img v-if="isImageFile(selectedFile)" :src="filePreviewUrl" alt="Предпросмотр" class="preview-image" />
        <div v-else class="file-info">
          <p>Имя файла: {{ selectedFile.name }}</p>
          <p>Размер: {{ formatFileSize(selectedFile.size) }}</p>
          <p>Тип: {{ selectedFile.type }}</p>
        </div>
      </div>
    </div>

    <div class="form-section">
      <div class="form-group">
        <label for="name">Название проекта *</label>
        <input
          type="text"
          id="name"
          v-model="name"
          :class="{ 'input-error': errors.name }"
          placeholder="Введите название проекта"
          maxlength="150"
        />
        <div v-if="errors.name" class="error-text">{{ errors.name }}</div>
      </div>

      <div class="form-group">
        <label for="code">Код проекта *</label>
        <input
          type="text"
          id="code"
          v-model="code"
          :class="{ 'input-error': errors.code }"
          placeholder="Например: PRJ"
          maxlength="5"
          @input="code = code.toUpperCase()"
        />
        <div v-if="errors.code" class="error-text">{{ errors.code }}</div>
        <p class="field-hint">Максимум 5 символов, только заглавные буквы и цифры</p>
      </div>
    </div>

    <div class="submit-section">
      <button @click="submitProject" :disabled="isSubmitting" class="submit-button">
        {{ isSubmitting ? 'Создание...' : 'Создать проект' }}
      </button>
      <div v-if="submitError" class="submit-error">{{ submitError }}</div>
    </div>
  </div>
</template>

<script setup>
import axios from '@/config/axiosConfig'
import { useAuthStore } from '@/stores/auth'
import { useProjectsStore } from '@/stores/projects'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const projectsStore = useProjectsStore()
const auth = useAuthStore()

const isLoading = ref(false)
const error = ref(null)
const isSubmitting = ref(false)
const submitError = ref(null)

const selectedFile = ref(null)
const filePreviewUrl = ref('')
const name = ref('')
const code = ref('')
const errors = ref({
  name: '',
  code: '',
})

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

  if (isImageFile(file)) {
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

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const validateForm = () => {
  let valid = true
  errors.value = { name: '', code: '' }

  if (!name.value.trim()) {
    errors.value.name = 'Название проекта обязательно'
    valid = false
  } else if (name.value.trim().length > 150) {
    errors.value.name = 'Название не должно превышать 150 символов'
    valid = false
  }

  if (!code.value.trim()) {
    errors.value.code = 'Код проекта обязателен'
    valid = false
  } else if (code.value.trim().length > 5) {
    errors.value.code = 'Код не должен превышать 5 символов'
    valid = false
  } else if (!/^[A-Z0-9]+$/.test(code.value)) {
    errors.value.code = 'Код должен содержать только заглавные буквы и цифры'
    valid = false
  }

  return valid
}

const submitProject = async () => {
  if (!validateForm()) {
    return
  }

  isSubmitting.value = true
  submitError.value = null

  try {
    const formData = new FormData()
    formData.append('name', name.value.trim())
    formData.append('code', code.value.trim())

    if (selectedFile.value) {
      formData.append('thumb', selectedFile.value)
    }

    await axios.post('/api/projects/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    projectsStore.fetchProjects()
    router.push({ name: 'home' })
  } catch (err) {
    submitError.value = 'Ошибка при создании проекта: ' + (err.response?.data?.detail || err.message)
    console.error(err)
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  // Нет предзагрузки данных, но можно проверить авторизацию
  if (!auth.user) {
    error.value = 'Требуется авторизация'
    isLoading.value = false
  } else {
    isLoading.value = false
  }
})
</script>

<style scoped>
.create-project {
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
  transition: background-color 0.2s;
}

.upload-button:hover {
  background-color: #1565c0;
}

.file-hint, .field-hint {
  font-size: 0.9em;
  color: #666;
  margin-top: 5px;
}

.file-preview {
  position: relative;
}

.preview-image {
  max-width: 100%;
  max-height: 400px;
  display: block;
  margin: 0 auto;
  border-radius: 4px;
}

.selected-file-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 15px;
}

.selected-file-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  text-align: start;
}

.remove-file-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background-color: #f44336;
  color: white;
  border: none;
  font-size: 24px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.remove-file-button:hover {
  background-color: #d32f2f;
}

.file-info {
  text-align: left;
  margin: 20px 0;
}

.form-section {
  margin-bottom: 30px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 16px;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #1976d2;
}

.input-error {
  border-color: #d32f2f;
}

.error-text {
  color: #d32f2f;
  font-size: 0.9em;
  margin-top: 5px;
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
  transition: background-color 0.2s;
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

@media (max-width: 768px) {
  .create-project {
    padding: 10px;
  }

  .file-preview-section {
    padding: 15px;
  }

  .file-upload-area {
    padding: 30px 15px;
  }

  .form-group input {
    padding: 8px;
    font-size: 15px;
  }

  .submit-button {
    padding: 10px 20px;
    font-size: 15px;
  }
}
</style>
