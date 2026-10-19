import { apiClient } from './client'
import type { ShotImportIn, ShotImportOut } from '@/types/api'

export function importShots(projectId: number, input: ShotImportIn) {
  return apiClient
    .post<ShotImportOut>(`/projects/${projectId}/shot-imports/`, input)
    .then((res) => res.data)
}
