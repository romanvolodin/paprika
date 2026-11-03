import { apiClient } from './client'
import type {
  CompanyCreateIn,
  CompanyListOut,
  CompanyListQuery,
  CompanyMemberListOut,
  CompanyMemberOut,
  CompanyMemberUpdateIn,
  CompanyOut,
  CompanyUpdateIn,
} from '@/types/api'

export function listCompanies(query: CompanyListQuery = {}) {
  return apiClient.get<CompanyListOut>('/companies/', { params: query }).then((res) => res.data)
}

export function getCompany(companyId: number) {
  return apiClient.get<CompanyOut>(`/companies/${companyId}/`).then((res) => res.data)
}

export function createCompany(input: CompanyCreateIn) {
  return apiClient.post<CompanyOut>('/companies/', input).then((res) => res.data)
}

export function updateCompany(companyId: number, input: CompanyUpdateIn) {
  return apiClient.patch<CompanyOut>(`/companies/${companyId}/`, input).then((res) => res.data)
}

export function deleteCompany(companyId: number) {
  return apiClient.delete<void>(`/companies/${companyId}/`)
}

export function listCompanyMembers(companyId: number) {
  return apiClient
    .get<CompanyMemberListOut>(`/companies/${companyId}/members/`)
    .then((res) => res.data)
}

export function updateCompanyMember(
  companyId: number,
  userId: number,
  input: CompanyMemberUpdateIn,
) {
  return apiClient
    .patch<CompanyMemberOut>(`/companies/${companyId}/members/${userId}/`, input)
    .then((res) => res.data)
}

export function removeCompanyMember(companyId: number, userId: number) {
  return apiClient.delete<void>(`/companies/${companyId}/members/${userId}/`)
}
