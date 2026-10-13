import { apiClient } from './client'
import type { VersionListOut, VersionListQuery, VersionOut } from '@/types/api'

export function listVersions(shotId: number, query: VersionListQuery = {}) {
  return apiClient
    .get<VersionListOut>(`/shots/${shotId}/versions/`, { params: query })
    .then((res) => res.data)
}

/**
 * Uploads a file as a new version. `onProgress` reports the bytes sent
 * so far; the request itself only resolves once the server has also
 * processed the file (metadata, thumbnail), which can take a while.
 */
export function uploadVersion(
  shotId: number,
  file: File,
  onProgress?: (loaded: number, total: number) => void,
) {
  const form = new FormData()
  form.append('source', file)
  return apiClient
    .post<VersionOut>(`/shots/${shotId}/versions/`, form, {
      onUploadProgress: (event) => {
        if (event.total) onProgress?.(event.loaded, event.total)
      },
    })
    .then((res) => res.data)
}

export function deleteVersion(versionId: number) {
  return apiClient.delete<void>(`/versions/${versionId}/`)
}
