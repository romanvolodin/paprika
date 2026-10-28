import type { Ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

/**
 * Rules for the members lists of a company and of a project, on top of
 * the permission that allows managing them. The backend is the one that
 * enforces permissions; these only decide what the interface offers.
 */
export function useMembershipPermissions(canManageMembers: Ref<boolean>) {
  const auth = useAuthStore()

  function isSelf(userId: number): boolean {
    return userId === auth.currentUser?.id
  }

  // Nobody removes themselves or changes their own role: doing so could
  // leave the company or project with no one able to fix it.
  function canRemoveMember(userId: number): boolean {
    return canManageMembers.value && !isSelf(userId)
  }

  function canChangeMemberRole(userId: number): boolean {
    return canManageMembers.value && !isSelf(userId)
  }

  return { canManageMembers, isSelf, canRemoveMember, canChangeMemberRole }
}
