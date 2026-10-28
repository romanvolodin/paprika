<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  useDialog,
  useMessage,
} from 'naive-ui'
import { storeToRefs } from 'pinia'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { PERMISSION } from '@/constants/permissions'
import { useShotDetailStore } from '@/stores/shotDetail'

const props = defineProps<{ companySlug: string; projectCode: string }>()

const router = useRouter()
const store = useShotDetailStore()
const message = useMessage()
const dialog = useDialog()
const { project } = storeToRefs(store)
const { can } = useProjectPermissions(project)
const canEditShot = computed(() => can(PERMISSION.shotEdit))
const canDeleteShot = computed(() => can(PERMISSION.shotDelete))

const groupIds = ref<number[]>([])
const recTimecode = ref<number | null>(null)
const duration = ref<number | null>(null)
const isSaving = ref(false)

const groupOptions = computed(() =>
  store.groups.map((group) => ({ label: group.name, value: group.id })),
)

watch(
  () => store.shot,
  (shot) => {
    if (!shot) return
    groupIds.value = [...shot.group_ids]
    recTimecode.value = shot.rec_timecode
    duration.value = shot.duration
  },
  { immediate: true },
)

async function handleSave() {
  isSaving.value = true
  try {
    await store.updateShot({
      group_ids: groupIds.value,
      rec_timecode: recTimecode.value,
      duration: duration.value,
    })
    message.success('Кадр обновлён.')
  } catch {
    message.error('Не удалось сохранить кадр. Проверьте введённые данные.')
  } finally {
    isSaving.value = false
  }
}

function confirmDelete() {
  if (!store.shot) return
  dialog.warning({
    title: 'Удалить кадр',
    content: `Удалить кадр ${store.shot.name}? Это действие необратимо.`,
    positiveText: 'Удалить',
    negativeText: 'Отмена',
    onPositiveClick: async () => {
      try {
        await store.deleteShot()
        message.success('Кадр удалён.')
        router.push({
          name: 'shot-list',
          params: { companySlug: props.companySlug, projectCode: props.projectCode },
        })
      } catch {
        message.error('Не удалось удалить кадр.')
      }
    },
  })
}
</script>

<template>
  <div v-if="store.shot" class="shot-settings">
    <section class="shot-settings__section">
      <h2 class="shot-settings__heading">Кадр</h2>
      <n-form label-placement="top" @submit.prevent="handleSave">
        <n-form-item label="Имя">
          <n-input :value="store.shot.name" disabled />
        </n-form-item>
        <p class="shot-settings__hint">Имя нельзя изменить после создания кадра.</p>

        <n-form-item label="Группы">
          <n-select
            v-model:value="groupIds"
            :options="groupOptions"
            :disabled="!canEditShot"
            multiple
            clearable
            placeholder="Без группы"
          />
        </n-form-item>

        <n-form-item label="Начало в монтаже, кадры">
          <n-input-number
            v-model:value="recTimecode"
            :disabled="!canEditShot"
            :min="0"
            :precision="0"
            clearable
          />
        </n-form-item>

        <n-form-item label="Длительность, кадры">
          <n-input-number
            v-model:value="duration"
            :disabled="!canEditShot"
            :min="1"
            :precision="0"
            clearable
          />
        </n-form-item>

        <n-button v-if="canEditShot" type="primary" :loading="isSaving" @click="handleSave">
          Сохранить
        </n-button>
      </n-form>
    </section>

    <section v-if="canDeleteShot" class="shot-settings__section">
      <h2 class="shot-settings__heading">Удаление кадра</h2>
      <div class="shot-settings__danger">
        <p class="shot-settings__hint shot-settings__hint--plain">
          Кадр будет удалён вместе со всеми версиями, задачами на кадре и чатом. Отменить это
          нельзя.
        </p>
        <n-button type="error" secondary @click="confirmDelete">Удалить кадр</n-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.shot-settings {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 480px;
}

.shot-settings__heading {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 var(--space-3);
}

.shot-settings__hint {
  margin: calc(var(--space-2) * -1) 0 var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.shot-settings__hint--plain {
  margin: 0;
}

.shot-settings__danger {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
}
</style>
