import { apiClient } from './client'
import type {
  InvitationCreateIn,
  InvitationInfoOut,
  InvitationListOut,
  InvitationOut,
  ProjectInvitationCreateIn,
  RegisterIn,
} from '@/types/api'

export function listCompanyInvitations(companyId: number) {
  return apiClient
    .get<InvitationListOut>(`/companies/${companyId}/invitations/`)
    .then((res) => res.data)
}

export function createCompanyInvitation(companyId: number, input: InvitationCreateIn) {
  return apiClient
    .post<InvitationOut>(`/companies/${companyId}/invitations/`, input)
    .then((res) => res.data)
}

export function createProjectInvitation(projectId: number, input: ProjectInvitationCreateIn) {
  return apiClient
    .post<InvitationOut>(`/projects/${projectId}/invitations/`, input)
    .then((res) => res.data)
}

export function renewInvitation(invitationId: number) {
  return apiClient
    .post<InvitationOut>(`/invitations/${invitationId}/renew/`)
    .then((res) => res.data)
}

export function revokeInvitation(invitationId: number) {
  return apiClient.delete(`/invitations/${invitationId}/`)
}

// The three below are what the person who got the link uses.

export function getInviteInfo(token: string) {
  return apiClient.get<InvitationInfoOut>(`/invite/${token}/`).then((res) => res.data)
}

export function registerByInvite(token: string, input: RegisterIn) {
  return apiClient.post(`/invite/${token}/register/`, input)
}

export function acceptInvite(token: string) {
  return apiClient.post(`/invite/${token}/accept/`)
}
