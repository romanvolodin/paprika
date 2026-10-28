<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  NButton,
  NCheckbox,
  NColorPicker,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NSwitch,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { TrashOutline } from '@vicons/ionicons5'
import type { PermissionOut, RoleOut } from '@/types/api'

export interface RoleFormValue {
  name: string
  color: string
  permissions: string[]
  sees_all_projects: boolean
}

// `role` is null while a new role is being made.
const props = defineProps<{
  role: RoleOut | null
  catalog: PermissionOut[]
  canEdit: boolean
  isSaving: boolean
}>()

const emit = defineEmits<{
  save: [value: RoleFormValue]
  remove: []
}>()

const DEFAULT_COLOR = '#888888'

const formRef = ref<FormInst | null>(null)
const name = ref('')
const color = ref(DEFAULT_COLOR)
const seesAllProjects = ref(false)
const permissions = ref<string[]>([])

watch(
  () => props.role,
  (role) => {
    name.value = role?.name ?? ''
    color.value = role?.color ?? DEFAULT_COLOR
    seesAllProjects.value = role?.sees_all_projects ?? false
    permissions.value = role ? [...role.permissions] : []
  },
  { immediate: true },
)

// The catalog arrives in display order; keep the sections in that order.
const groups = computed(() => {
  const result: { title: string; level: string; items: PermissionOut[] }[] = []
  for (const permission of props.catalog) {
    let group = result.find((candidate) => candidate.title === permission.group)
    if (!group) {
      group = { title: permission.group, level: permission.level, items: [] }
      result.push(group)
    }
    group.items.push(permission)
  }
  return result
})

function levelHint(level: string): string {
  return level === 'company'
    ? 'Действуют по роли человека в компании'
    : 'Действуют по роли человека в проекте'
}

function isChecked(code: string): boolean {
  return permissions.value.includes(code)
}

function toggle(code: string, checked: boolean) {
  permissions.value = checked
    ? [...permissions.value, code]
    : permissions.value.filter((item) => item !== code)
}

const rules: FormRules = {
  name: [{ required: true, message: 'Введите название', trigger: ['input', 'blur'] }],
}

const formModel = computed(() => ({ name: name.value }))

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  emit('save', {
    name: name.value.trim(),
    color: color.value,
    permissions: permissions.value,
    sees_all_projects: seesAllProjects.value,
  })
}
</script>

<template>
  <n-form
    ref="formRef"
    class="role-editor"
    :model="formModel"
    :rules="rules"
    label-placement="top"
    :disabled="!canEdit"
    @submit.prevent="handleSave"
  >
    <h2 class="role-editor__title">{{ role ? role.name : 'Новая роль' }}</h2>

    <div class="role-editor__row">
      <n-form-item label="Название" path="name" class="role-editor__name">
        <n-input v-model:value="name" maxlength="100" />
      </n-form-item>
      <n-form-item label="Цвет">
        <n-color-picker v-model:value="color" :modes="['hex']" :show-alpha="false" />
      </n-form-item>
    </div>

    <div class="role-editor__scope">
      <n-switch v-model:value="seesAllProjects" aria-label="Видит все проекты компании" />
      <div>
        <div class="role-editor__scope-title">Видит все проекты компании</div>
        <div class="role-editor__hint">
          Иначе человек видит только те проекты, в которые его добавили.
        </div>
      </div>
    </div>

    <section v-for="group in groups" :key="group.title" class="role-editor__group">
      <h3 class="role-editor__group-title">{{ group.title }}</h3>
      <p class="role-editor__hint">{{ levelHint(group.level) }}</p>
      <ul class="role-editor__permissions">
        <li v-for="permission in group.items" :key="permission.code">
          <n-checkbox
            :checked="isChecked(permission.code)"
            @update:checked="(checked: boolean) => toggle(permission.code, checked)"
          >
            <span class="role-editor__permission-label">{{ permission.label }}</span>
            <span class="role-editor__hint"> {{ permission.description }}</span>
          </n-checkbox>
        </li>
      </ul>
    </section>

    <div v-if="canEdit" class="role-editor__actions">
      <n-button type="primary" attr-type="submit" :loading="isSaving">
        {{ role ? 'Сохранить' : 'Создать роль' }}
      </n-button>
      <n-button v-if="role" type="error" quaternary :disabled="isSaving" @click="emit('remove')">
        <template #icon><n-icon :component="TrashOutline" /></template>
        Удалить
      </n-button>
    </div>
  </n-form>
</template>

<style scoped>
.role-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.role-editor__title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
}

.role-editor__row {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
}

.role-editor__name {
  flex: 1;
}

.role-editor__scope {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
}

.role-editor__scope-title,
.role-editor__group-title {
  font-weight: 600;
}

.role-editor__group-title {
  margin: 0;
  font-size: 0.95rem;
}

.role-editor__group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.role-editor__hint {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm, 13px);
}

.role-editor__permissions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.role-editor__permission-label {
  font-weight: 500;
}

.role-editor__actions {
  display: flex;
  gap: var(--space-2);
}
</style>
