<script setup lang="ts">
import { computed } from 'vue'
import type { PermissionOut, RoleOut } from '@/types/api'

const props = defineProps<{ roles: RoleOut[]; catalog: PermissionOut[] }>()

const emit = defineEmits<{ select: [roleId: number] }>()

// Rows follow the catalog order, with a heading row before each section.
const rows = computed(() => {
  const result: ({ kind: 'group'; title: string } | { kind: 'permission'; item: PermissionOut })[] =
    []
  let current: string | null = null
  for (const permission of props.catalog) {
    if (permission.group !== current) {
      current = permission.group
      result.push({ kind: 'group', title: current })
    }
    result.push({ kind: 'permission', item: permission })
  }
  return result
})

function has(role: RoleOut, code: string): boolean {
  return role.permissions.includes(code)
}
</script>

<template>
  <div class="role-matrix">
    <table class="role-matrix__table">
      <thead>
        <tr>
          <th scope="col" class="role-matrix__corner"></th>
          <th v-for="role in roles" :key="role.id" scope="col">
            <button class="role-matrix__role" type="button" @click="emit('select', role.id)">
              <span class="role-matrix__dot" :style="{ background: role.color }"></span>
              {{ role.name }}
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr class="role-matrix__scope-row">
          <th scope="row">Видит все проекты компании</th>
          <td v-for="role in roles" :key="role.id">
            <span
              :class="role.sees_all_projects ? 'role-matrix__yes' : 'role-matrix__no'"
              :aria-label="role.sees_all_projects ? 'Да' : 'Нет'"
              >{{ role.sees_all_projects ? '✓' : '—' }}</span
            >
          </td>
        </tr>
        <template v-for="row in rows" :key="row.kind === 'group' ? row.title : row.item.code">
          <tr v-if="row.kind === 'group'" class="role-matrix__group">
            <th :colspan="roles.length + 1" scope="colgroup">{{ row.title }}</th>
          </tr>
          <tr v-else>
            <th scope="row" :title="row.item.description">{{ row.item.label }}</th>
            <td v-for="role in roles" :key="role.id">
              <span
                :class="has(role, row.item.code) ? 'role-matrix__yes' : 'role-matrix__no'"
                :aria-label="has(role, row.item.code) ? 'Есть' : 'Нет'"
                >{{ has(role, row.item.code) ? '✓' : '—' }}</span
              >
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.role-matrix {
  overflow-x: auto;
}

.role-matrix__table {
  border-collapse: collapse;
  width: 100%;
  font-size: var(--text-sm, 13px);
}

.role-matrix__table th,
.role-matrix__table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  text-align: center;
}

.role-matrix__table tbody th[scope='row'] {
  text-align: left;
  font-weight: 400;
}

.role-matrix__corner {
  min-width: 220px;
}

.role-matrix__group th {
  text-align: left;
  font-weight: 600;
  background: var(--color-surface-muted);
}

.role-matrix__role {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: none;
  border: none;
  color: inherit;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.role-matrix__role:hover {
  color: var(--color-accent);
}

.role-matrix__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.role-matrix__yes {
  color: var(--color-accent);
  font-weight: 700;
}

.role-matrix__no {
  color: var(--color-text-tertiary);
}
</style>
