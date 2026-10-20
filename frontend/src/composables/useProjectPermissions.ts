import { computed, type Ref } from 'vue'
import { useMembershipPermissions } from './useMembershipPermissions'
import type { ProjectMemberOut } from '@/types/api'

/**
 * Project-flavored view over `useMembershipPermissions` - see there for
 * the shared rules, and `useCompanyPermissions` for the company-side
 * equivalent.
 *
 * `canWrite` mirrors the backend's `require_can_write`: every project
 * member except the read-only `client` role may change shots (and,
 * later, versions, tasks and chat).
 *
 * `canManageProject` mirrors `require_can_manage_project`: only admins
 * and producers see the project settings and may delete the project.
 */
export function useProjectPermissions(members: Ref<ProjectMemberOut[]>) {
  const { canEdit, currentRole, ...rest } = useMembershipPermissions(members)

  const canWrite = computed(() => currentRole.value !== null && currentRole.value !== 'client')

  const canManageProject = computed(
    () => currentRole.value === 'admin' || currentRole.value === 'producer',
  )

  return { canEditProject: canEdit, currentRole, canWrite, canManageProject, ...rest }
}
