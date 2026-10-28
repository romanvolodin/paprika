import { apiClient } from './client'
import type { RoleListOut } from '@/types/api'

export function listCompanyRoles(companyId: number) {
  return apiClient.get<RoleListOut>(`/companies/${companyId}/roles/`).then((res) => res.data)
}
