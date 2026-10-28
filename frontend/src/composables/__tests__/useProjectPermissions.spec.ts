import { beforeEach, describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { PERMISSION } from '@/constants/permissions'
import { useAuthStore } from '@/stores/auth'
import type { ProjectOut, UserOut } from '@/types/api'

function buildUser(overrides: Partial<UserOut> = {}): UserOut {
  return {
    id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    avatar: null,
    is_active: true,
    date_joined: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function buildProject(myPermissions: string[]): ProjectOut {
  return {
    id: 1,
    company_id: 1,
    name: 'Project',
    code: 'PRJ',
    description: '',
    cover: null,
    start_date: null,
    deadline: null,
    is_active: true,
    my_permissions: myPermissions,
    created_by: null,
    updated_by: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  } as ProjectOut
}

describe('useProjectPermissions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useAuthStore().currentUser = buildUser({ id: 1 })
  })

  it('answers can() from the permissions the API sent with the project', () => {
    const project = ref<ProjectOut | null>(buildProject([PERMISSION.shotCreate]))

    const { can } = useProjectPermissions(project)

    expect(can(PERMISSION.shotCreate)).toBe(true)
    expect(can(PERMISSION.shotDelete)).toBe(false)
  })

  it('grants nothing while there is no project', () => {
    const { can, canEditProject, canOpenSettings } = useProjectPermissions(ref(null))

    expect(can(PERMISSION.chatWrite)).toBe(false)
    expect(canEditProject.value).toBe(false)
    expect(canOpenSettings.value).toBe(false)
  })

  it('follows the project as it is reloaded', () => {
    const project = ref<ProjectOut | null>(buildProject([]))
    const { can } = useProjectPermissions(project)

    project.value = buildProject([PERMISSION.versionUpload])

    expect(can(PERMISSION.versionUpload)).toBe(true)
  })

  it.each([
    ['project.edit', PERMISSION.projectEdit],
    ['project.delete', PERMISSION.projectDelete],
    ['project.members', PERMISSION.projectMembers],
  ])('opens the settings for someone with %s', (_label, code) => {
    const { canOpenSettings } = useProjectPermissions(ref(buildProject([code])))

    expect(canOpenSettings.value).toBe(true)
  })

  it('keeps the settings closed to someone who can change nothing there', () => {
    const { canOpenSettings } = useProjectPermissions(
      ref(buildProject([PERMISSION.shotCreate, PERMISSION.chatWrite])),
    )

    expect(canOpenSettings.value).toBe(false)
  })

  it('exposes the members rules on top of project.members', () => {
    const managers = useProjectPermissions(ref(buildProject([PERMISSION.projectMembers])))
    const others = useProjectPermissions(ref(buildProject([])))

    expect(managers.canManageMembers.value).toBe(true)
    expect(managers.canRemoveMember(2)).toBe(true)
    expect(managers.canRemoveMember(1)).toBe(false)
    expect(others.canManageMembers.value).toBe(false)
    expect(others.canRemoveMember(2)).toBe(false)
  })
})
