import { computed, type Ref } from 'vue'
import { useMembershipPermissions } from './useMembershipPermissions'
import { PERMISSION, type PermissionCode } from '@/constants/permissions'
import type { ProjectOut } from '@/types/api'

/**
 * What the current user may do in the project, from the `my_permissions`
 * the API sends with it - one `can(code)` for any permission, plus a few
 * shortcuts for the ones several screens ask about. See
 * `useMembershipPermissions` for the members list rules.
 */
export function useProjectPermissions(project: Ref<ProjectOut | null>) {
  function can(code: PermissionCode): boolean {
    return project.value?.my_permissions?.includes(code) ?? false
  }

  const canEditProject = computed(() => can(PERMISSION.projectEdit))
  const canDeleteProject = computed(() => can(PERMISSION.projectDelete))
  const canManageMembers = computed(() => can(PERMISSION.projectMembers))
  // The project settings page is for anyone who can change something there.
  const canOpenSettings = computed(
    () => canEditProject.value || canDeleteProject.value || canManageMembers.value,
  )

  // Until the project is loaded nothing is hidden, so no "assigned to
  // you" wording flashes up for people who see everything.
  const seesAllShots = computed(() => project.value?.my_sees_all_shots ?? true)

  return {
    can,
    seesAllShots,
    canEditProject,
    canDeleteProject,
    canOpenSettings,
    ...useMembershipPermissions(canManageMembers),
  }
}
