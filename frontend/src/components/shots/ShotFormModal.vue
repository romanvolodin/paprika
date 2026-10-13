<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import type { ShotGroupOut, ShotOut, ShotStatusOut } from '@/types/api'

export interface ShotFormValues {
  name: string
  status_id: number
  group_ids: number[]
  rec_timecode: number | null
  duration: number | null
}

const props = defineProps<{
  show: boolean
  // The name is set once and can't be changed afterwards, so in edit
  // mode it is only displayed.
  mode: 'create' | 'edit'
  shot?: ShotOut | null
  statuses: ShotStatusOut[]
  groups: ShotGroupOut[]
  isSubmitting: boolean
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  submit: [values: ShotFormValues]
}>()

const formRef = ref<FormInst | null>(null)
const name = ref('')
const statusId = ref<number | null>(null)
const groupIds = ref<number[]>([])
const recTimecode = ref<number | null>(null)
const duration = ref<number | null>(null)

const statusOptions = computed(() =>
  props.statuses.map((status) => ({ label: status.name, value: status.id })),
)
const groupOptions = computed(() =>
  props.groups.map((group) => ({ label: group.name, value: group.id })),
)

watch(
  () => props.show,
  (isShown) => {
    if (!isShown) return
    if (props.mode === 'edit' && props.shot) {
      name.value = props.shot.name
      statusId.value = props.shot.status_id
      groupIds.value = [...props.shot.group_ids]
      recTimecode.value = props.shot.rec_timecode
      duration.value = props.shot.duration
    } else {
      name.value = ''
      statusId.value = props.statuses.find((status) => status.is_default)?.id ?? null
      groupIds.value = []
      recTimecode.value = null
      duration.value = null
    }
  },
)

// Mirrors the backend rule: the name ends up in the shot's URL.
const NAME_PATTERN = /^[^/\s]+$/

const rules: FormRules = {
  name: [
    { required: true, message: 'Введите имя кадра', trigger: 'blur' },
    {
      validator: (_rule, value: string) => !value || NAME_PATTERN.test(value),
      message: 'Имя не должно содержать пробелы и слэши',
      trigger: ['blur', 'input'],
    },
  ],
  statusId: [{ required: true, type: 'number', message: 'Выберите статус', trigger: 'change' }],
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  emit('submit', {
    name: name.value,
    status_id: statusId.value as number,
    group_ids: groupIds.value,
    rec_timecode: recTimecode.value,
    duration: duration.value,
  })
}
</script>

<template>
  <n-modal
    :show="show"
    preset="card"
    :title="mode === 'create' ? 'Новый кадр' : 'Изменить кадр'"
    style="max-width: 480px"
    :mask-closable="!isSubmitting"
    @update:show="emit('update:show', $event)"
  >
    <n-form
      ref="formRef"
      :model="{ name, statusId }"
      :rules="rules"
      label-placement="top"
      @submit.prevent="handleSubmit"
    >
      <n-form-item label="Имя" path="name">
        <n-input v-model:value="name" :disabled="mode === 'edit'" placeholder="Например, 0010" />
      </n-form-item>
      <p v-if="mode === 'edit'" class="shot-form__hint">
        Имя нельзя изменить после создания кадра.
      </p>

      <n-form-item label="Статус" path="statusId">
        <n-select v-model:value="statusId" :options="statusOptions" />
      </n-form-item>

      <n-form-item label="Группы">
        <n-select
          v-model:value="groupIds"
          :options="groupOptions"
          multiple
          clearable
          placeholder="Без группы"
        />
      </n-form-item>

      <n-form-item label="Начало в монтаже, кадры">
        <n-input-number v-model:value="recTimecode" :min="0" :precision="0" clearable />
      </n-form-item>

      <n-form-item label="Длительность, кадры">
        <n-input-number v-model:value="duration" :min="1" :precision="0" clearable />
      </n-form-item>
    </n-form>

    <template #footer>
      <div class="shot-form__actions">
        <n-button :disabled="isSubmitting" @click="emit('update:show', false)">Отмена</n-button>
        <n-button type="primary" :loading="isSubmitting" @click="handleSubmit">
          {{ mode === 'create' ? 'Создать' : 'Сохранить' }}
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<style scoped>
.shot-form__hint {
  margin: calc(var(--space-2) * -1) 0 var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.shot-form__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
