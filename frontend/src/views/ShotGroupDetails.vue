<script setup>
import axios from '@/config/axiosConfig'
import { onMounted, ref, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useShotsStore } from '@/stores/shots'

const route = useRoute()
const router = useRouter()
const shotsStore = useShotsStore()

const projectCode = route.params.projectCode
const shotGroupId = route.params.shotGroupId

const _shotGroup = ref(null)
const _loaded = ref(false)
const _error = ref(null)
const _deleteError = ref(null)
const _showDeleteDialog = ref(false)

onMounted(async () => {
  await fetchShotGroup()
})

async function fetchShotGroup() {
  try {
    const response = await axios.get(`/api/projects/${projectCode}/shot-groups/${shotGroupId}`)
    _shotGroup.value = response.data
  } catch (error) {
    _error.value = `${error.status}: ${error.response.data.detail}`
    _shotGroup.value = null
  } finally {
    _loaded.value = true
  }
}

async function deleteShotGroup() {
  _deleteError.value = null

  // Проверка на удаление группы по умолчанию
  if (_shotGroup.value.is_default) {
    _deleteError.value = 'Невозможно удалить группу по умолчанию'
    _showDeleteDialog.value = false
    return
  }

  // Проверка на удаление корневой группы
  if (_shotGroup.value.is_root) {
    _deleteError.value = 'Невозможно удалить корневую группу'
    _showDeleteDialog.value = false
    return
  }

  try {
    await shotsStore.deleteShotGroup(projectCode, shotGroupId)
    router.push({ name: 'shot-groups-by-project', params: { projectCode } })
  } catch (error) {
    if (error.status === 403) {
      _deleteError.value = 'У вас нет прав доступа для удаления этой группы'
    } else {
      _deleteError.value = `Ошибка при удалении группы: ${error.response?.data?.detail || error.message}`
    }
  } finally {
    _showDeleteDialog.value = false
  }
}

watchEffect(() => {
  if (_shotGroup.value) {
    document.title = `${projectCode}: ${_shotGroup.value.name}`
  }
})
</script>

<template>
  <div v-if="!_loaded" class="empty">Загрузка...</div>

  <div v-else-if="_error" class="error">
    {{ _error }}
  </div>

  <div v-else>
    <div class="group-header">
      <h1>
        {{ _shotGroup.name }}
        <sub>({{ _shotGroup.shots.length }})</sub>
      </h1>

      <button
        v-if="!_shotGroup.is_default && !_shotGroup.is_root"
        @click="_showDeleteDialog = true"
        class="delete-button"
      >
        Удалить группу
      </button>
    </div>

    <div v-if="_deleteError" class="error">
      {{ _deleteError }}
    </div>

    <div class="shots-grid">
      <div v-for="shot in _shotGroup.shots" :key="shot.id" class="shot-card">
        <router-link
          :to="{
            name: 'shot-details',
            params: { projectCode: projectCode, shotName: shot.name },
          }"
        >
          <img v-if="shot.thumb" :src="shot.thumb" :alt="shot.name" class="shot-image" />
          <div v-else class="shot-no-thumb">Нет превью</div>
          <div class="shot-info">
            {{ shot.name }}
          </div>
        </router-link>
      </div>
    </div>

    <!-- Диалог подтверждения удаления -->
    <div v-if="_showDeleteDialog" class="modal-overlay" @click="_showDeleteDialog = false">
      <div class="modal-content" @click.stop>
        <h2>Подтверждение удаления</h2>
        <p>Вы уверены, что хотите удалить группу "{{ _shotGroup.name }}"?</p>
        <p>Это действие нельзя отменить.</p>
        <div class="modal-actions">
          <button @click="_showDeleteDialog = false" class="cancel-button">Отмена</button>
          <button @click="deleteShotGroup" class="confirm-button">Удалить</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.error {
  margin: 2rem;
  border: 1px solid #c41212;
  border-radius: 4px;
  background-color: #ffe6e6;
  padding: 1rem;
  color: #c41212;
  font-weight: bold;
}
.empty {
  display: flex;
  flex-grow: 1;
  justify-content: center;
  align-items: center;
}
.shots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 5px;
}
.shot-card {
  transition: transform 0.1s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.shot-card:hover {
  transform: translateY(-4px);
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

.shot-info {
  padding: 2px 5px;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.delete-button {
  cursor: pointer;
  border: none;
  border-radius: 4px;
  background-color: #c41212;
  padding: 0.5rem 1rem;
  color: white;
}

.delete-button:hover {
  background-color: #a50f0f;
}

.modal-overlay {
  display: flex;
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  background-color: rgba(0, 0, 0, 0.5);
}

.modal-content {
  border-radius: 8px;
  background: white;
  padding: 2rem;
  width: 90%;
  max-width: 500px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
}

.cancel-button,
.confirm-button {
  cursor: pointer;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 1rem;
}

.cancel-button {
  background-color: #ddd;
}

.confirm-button {
  background-color: #c41212;
  color: white;
}
</style>
