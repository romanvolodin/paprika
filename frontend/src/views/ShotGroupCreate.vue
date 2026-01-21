<script setup>
import axios from '@/config/axiosConfig'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const projectCode = route.params.projectCode

const _loading = ref(false)
const _error = ref(null)
const _success = ref(false)

// Form data
const groupName = ref('')
const isRoot = ref(true)
const isDefault = ref(false)

// Validation
const formErrors = ref({})

function validateForm() {
  formErrors.value = {}

  if (!groupName.value.trim()) {
    formErrors.value.name = 'Название группы обязательно'
  }

  return Object.keys(formErrors.value).length === 0
}

async function createShotGroup() {
  if (!validateForm()) {
    return
  }

  _loading.value = true
  _error.value = null
  _success.value = false

  try {
    const groupData = {
      name: groupName.value.trim(),
      is_root: isRoot.value,
      is_default: isDefault.value,
    }

    const response = await axios.post(`/api/projects/${projectCode}/shot-groups/create`, [
      groupData,
    ])

    if (response.data.shot_groups > 0) {
      _success.value = true
      // Reset form
      groupName.value = ''
      isRoot.value = true
      isDefault.value = false
      // Redirect to groups list after short delay
      setTimeout(() => {
        router.push({ name: 'shot-groups-by-project', params: { projectCode } })
      }, 1500)
    }
  } catch (error) {
    _error.value =
      error.response?.data?.errors?.[0]?.name ||
      error.response?.data?.detail ||
      'Ошибка при создании группы'

    // Handle field-specific errors
    if (error.response?.data?.errors) {
      const errors = error.response.data.errors[0] || {}
      if (errors.name) {
        formErrors.value.name = errors.name[0]
      }
    }
  } finally {
    _loading.value = false
  }
}
</script>

<template>
  <div class="create-shot-group">
    <h1>Создать группу шотов</h1>

    <form @submit.prevent="createShotGroup" class="group-form">
      <div class="form-group">
        <label for="groupName">Название группы *</label>
        <input
          id="groupName"
          v-model="groupName"
          type="text"
          :class="{ 'is-invalid': formErrors.name }"
          placeholder="Введите название группы"
          :disabled="_loading"
        />
        <div v-if="formErrors.name" class="invalid-feedback">
          {{ formErrors.name }}
        </div>
      </div>

      <div class="form-group">
        <label class="checkbox-label">
          <input v-model="isRoot" type="checkbox" :disabled="_loading" />
          Корневая группа
        </label>
        <p class="help-text">Корневые группы отображаются в основном списке шотов</p>
      </div>

      <div class="form-group">
        <label class="checkbox-label">
          <input v-model="isDefault" type="checkbox" :disabled="_loading" />
          Группа по умолчанию
        </label>
        <p class="help-text">Группа, в которую будут добавляться новые шоты по умолчанию</p>
      </div>

      <div v-if="_error" class="error-message">
        {{ _error }}
      </div>

      <div v-if="_success" class="success-message">Группа успешно создана! Перенаправление...</div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary" :disabled="_loading || _success">
          <span v-if="_loading">Создание...</span>
          <span v-else>Создать группу</span>
        </button>

        <router-link
          :to="{ name: 'shot-groups-by-project', params: { projectCode } }"
          class="btn btn-secondary"
        >
          Отмена
        </router-link>
      </div>
    </form>
  </div>
</template>

<style scoped>
.create-shot-group {
  margin: 0 auto;
  padding: 20px;
  max-width: 600px;
}

.group-form {
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  background: var(--card-bg);
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-color);
  font-weight: 500;
}

.checkbox-label {
  display: flex;
  align-items: center;
  margin-bottom: 0;
  font-weight: normal;
}

.checkbox-label input {
  margin-right: 8px;
}

input[type='text'] {
  transition: border-color 0.2s;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: var(--input-bg);
  padding: 12px;
  width: 100%;
  color: var(--text-color);
  font-size: 16px;
}

input[type='text']:focus {
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
  border-color: #007bff;
}

input[type='text']:disabled {
  cursor: not-allowed;
  background-color: #f5f5f5;
}

input[type='checkbox'] {
  margin-right: 8px;
  width: 18px;
  height: 18px;
}

.help-text {
  margin-top: 4px;
  color: #666;
  font-size: 14px;
}

.is-invalid {
  border-color: #dc3545 !important;
}

.invalid-feedback {
  display: block;
  margin-top: 0.25rem;
  width: 100%;
  color: #dc3545;
  font-size: 80%;
}

.error-message {
  margin: 20px 0;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
  background-color: #f8d7da;
  padding: 12px;
  color: #721c24;
}

.success-message {
  margin: 20px 0;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
  background-color: #d4edda;
  padding: 12px;
  color: #155724;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 30px;
}

.btn {
  display: inline-block;
  transition: background-color 0.2s;
  cursor: pointer;
  border: none;
  border-radius: 4px;
  padding: 10px 20px;
  font-size: 16px;
  text-align: center;
  text-decoration: none;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0056b3;
}

.btn-primary:disabled {
  cursor: not-allowed;
  background-color: #6c757d;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background-color: #545b62;
}
</style>
