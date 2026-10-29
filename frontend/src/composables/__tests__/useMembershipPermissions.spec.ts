import { beforeEach, describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { useMembershipPermissions } from '@/composables/useMembershipPermissions'
import { useAuthStore } from '@/stores/auth'
import type { MeOut } from '@/types/api'

function buildUser(overrides: Partial<MeOut> = {}): MeOut {
  return {
    id: 1,
    email: 'a@paprika.dev',
    first_name: 'A',
    last_name: 'One',
    avatar: null,
    is_active: true,
    date_joined: '2026-01-01T00:00:00Z',
    is_superuser: false,
    must_change_password: false,
    ...overrides,
  }
}

describe('useMembershipPermissions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useAuthStore().currentUser = buildUser({ id: 1 })
  })

  it('lets someone who can manage members remove and re-role others', () => {
    const { canRemoveMember, canChangeMemberRole } = useMembershipPermissions(ref(true))

    expect(canRemoveMember(2)).toBe(true)
    expect(canChangeMemberRole(2)).toBe(true)
  })

  it('never lets anyone remove themselves or change their own role', () => {
    const { canRemoveMember, canChangeMemberRole, isSelf } = useMembershipPermissions(ref(true))

    expect(isSelf(1)).toBe(true)
    expect(canRemoveMember(1)).toBe(false)
    expect(canChangeMemberRole(1)).toBe(false)
  })

  it('offers nothing to someone who cannot manage members', () => {
    const { canRemoveMember, canChangeMemberRole } = useMembershipPermissions(ref(false))

    expect(canRemoveMember(2)).toBe(false)
    expect(canChangeMemberRole(2)).toBe(false)
  })

  it('follows the permission as it changes', () => {
    const canManage = ref(false)
    const { canRemoveMember } = useMembershipPermissions(canManage)

    canManage.value = true

    expect(canRemoveMember(2)).toBe(true)
  })

  it('is not self for someone else or when nobody is signed in', () => {
    const auth = useAuthStore()
    const { isSelf } = useMembershipPermissions(ref(true))

    expect(isSelf(2)).toBe(false)
    auth.currentUser = null
    expect(isSelf(1)).toBe(false)
  })
})
