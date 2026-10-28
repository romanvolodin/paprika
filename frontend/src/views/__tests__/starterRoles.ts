import type { ProjectOut, RoleRefOut } from '@/types/api'

// The starter roles of a new company and the project permissions each gives
// (see `apps/access/permissions.py`), so a spec can say "as an executor".
export type StarterRole =
  | 'admin'
  | 'producer'
  | 'coordinator'
  | 'executor'
  | 'freelancer'
  | 'client'
  // A custom role with no permissions at all.
  | 'readonly'

const PROJECT_WORK = [
  'project.edit',
  'project.members',
  'feed.view',
  'shot.create',
  'shot.edit',
  'shot.delete',
  'shot.import',
  'group.manage',
  'task.create',
  'task.edit',
  'task.delete',
  'task.update_own',
  'version.upload',
  'version.delete',
  'version.delete_own',
  'chat.write',
  'chat.edit_any',
]

const PROJECT_PERMISSIONS: Record<StarterRole, string[]> = {
  admin: [...PROJECT_WORK, 'project.delete'],
  producer: [...PROJECT_WORK, 'project.delete'],
  coordinator: PROJECT_WORK,
  executor: ['feed.view', 'task.update_own', 'version.upload', 'version.delete_own', 'chat.write'],
  freelancer: ['task.update_own', 'version.upload', 'version.delete_own', 'chat.write'],
  client: ['chat.write'],
  readonly: [],
}

const NAMES: Record<StarterRole, string> = {
  admin: 'Админ',
  producer: 'Продюсер',
  coordinator: 'Координатор',
  executor: 'Исполнитель',
  freelancer: 'Фрилансер',
  client: 'Клиент',
  readonly: 'Только просмотр',
}

export function roleRefOf(role: StarterRole): RoleRefOut {
  return { id: Object.keys(NAMES).indexOf(role) + 1, name: NAMES[role], color: '#00A64F' }
}

export function buildProjectFor(
  role: StarterRole,
  overrides: Partial<ProjectOut> = {},
): ProjectOut {
  return {
    id: 1,
    company_id: 7,
    name: 'Feature Film',
    code: 'PRJ',
    description: '',
    cover: null,
    start_date: null,
    deadline: null,
    is_active: true,
    my_permissions: PROJECT_PERMISSIONS[role],
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}
