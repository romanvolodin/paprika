import { beforeEach, describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectPermissions } from '@/composables/useProjectPermissions'
import { useAuthStore } from '@/stores/auth'
import type { ProjectMemberOut, UserOut } from '@/types/api'

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

function buildMember(overrides: Partial<ProjectMemberOut> = {}): ProjectMemberOut {
  return {
    id: 1,
    user_id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    role: 'executor',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('useProjectPermissions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // The underlying rules are fully covered by useMembershipPermissions'
  // own tests - this just confirms the wrapper renames `canEdit` to
  // `canEditProject` and wires real `ProjectMemberOut` rows through.
  it('exposes canEditProject for a project admin', () => {
    const auth = useAuthStore()
    auth.currentUser = buildUser({ id: 1 })
    const members = ref<ProjectMemberOut[]>([buildMember({ user_id: 1, role: 'admin' })])

    const { canEditProject, canManageMembers } = useProjectPermissions(members)

    expect(canEditProject.value).toBe(true)
    expect(canManageMembers.value).toBe(true)
  })

  it('a non-admin project member cannot edit the project', () => {
    const auth = useAuthStore()
    auth.currentUser = buildUser({ id: 1 })
    const members = ref<ProjectMemberOut[]>([buildMember({ user_id: 1, role: 'executor' })])

    const { canEditProject } = useProjectPermissions(members)

    expect(canEditProject.value).toBe(false)
  })

  it.each([
    ['admin', true],
    ['producer', true],
    ['coordinator', true],
    ['executor', true],
    ['freelancer', true],
    ['client', false],
  ] as const)('canWrite for role %s is %s', (role, expected) => {
    const auth = useAuthStore()
    auth.currentUser = buildUser({ id: 1 })
    const members = ref<ProjectMemberOut[]>([buildMember({ user_id: 1, role })])

    const { canWrite } = useProjectPermissions(members)

    expect(canWrite.value).toBe(expected)
  })

  it('canWrite is false when the user is not among the members', () => {
    const auth = useAuthStore()
    auth.currentUser = buildUser({ id: 1 })
    const members = ref<ProjectMemberOut[]>([buildMember({ user_id: 2, role: 'admin' })])

    const { canWrite } = useProjectPermissions(members)

    expect(canWrite.value).toBe(false)
  })
})
