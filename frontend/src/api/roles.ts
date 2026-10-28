import { apiClient } from './client'
import type {
  PermissionListOut,
  RoleCreateIn,
  RoleListOut,
  RoleOut,
  RoleUpdateIn,
} from '@/types/api'

export function listPermissions() {
  return apiClient.get<PermissionListOut>('/permissions/').then((res) => res.data)
}

export function listCompanyRoles(companyId: number) {
  return apiClient.get<RoleListOut>(`/companies/${companyId}/roles/`).then((res) => res.data)
}

export function createRole(companyId: number, input: RoleCreateIn) {
  return apiClient.post<RoleOut>(`/companies/${companyId}/roles/`, input).then((res) => res.data)
}

export function updateRole(roleId: number, input: RoleUpdateIn) {
  return apiClient.patch<RoleOut>(`/roles/${roleId}/`, input).then((res) => res.data)
}

export function deleteRole(roleId: number) {
  return apiClient.delete(`/roles/${roleId}/`)
}
