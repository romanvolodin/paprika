import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as versionsApi from '@/api/versions'
import type { VersionOut } from '@/types/api'

// `processing` is the stretch after the last byte was sent while the
// server still analyses the file and makes its thumbnail - the upload
// request only resolves when that is done.
export type UploadState = 'idle' | 'uploading' | 'processing'

export const useVersionsStore = defineStore('versions', () => {
  const items = ref<VersionOut[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const isLoading = ref(false)
  const uploadState = ref<UploadState>('idle')
  const uploadProgress = ref(0)

  // The store is shared by every shot page, so a response for a shot
  // the user already left must not overwrite the current one.
  let loadedShotId: number | null = null
  let fetchToken = 0

  async function fetch(shotId: number) {
    const token = ++fetchToken
    if (loadedShotId !== shotId) {
      items.value = []
      total.value = 0
      page.value = 1
      loadedShotId = shotId
    }
    isLoading.value = true
    try {
      const result = await versionsApi.listVersions(shotId, {
        page: page.value,
        page_size: pageSize.value,
      })
      if (token !== fetchToken) return
      items.value = result.items
      total.value = result.total
    } finally {
      if (token === fetchToken) isLoading.value = false
    }
  }

  async function setPage(shotId: number, value: number) {
    page.value = value
    await fetch(shotId)
  }

  async function upload(shotId: number, file: File) {
    uploadState.value = 'uploading'
    uploadProgress.value = 0
    try {
      await versionsApi.uploadVersion(shotId, file, (loaded, size) => {
        uploadProgress.value = Math.round((loaded / size) * 100)
        if (loaded >= size) uploadState.value = 'processing'
      })
    } finally {
      uploadState.value = 'idle'
      uploadProgress.value = 0
    }
    // The newest version is on the first page.
    page.value = 1
    await fetch(shotId)
  }

  async function remove(shotId: number, versionId: number) {
    await versionsApi.deleteVersion(versionId)
    await fetch(shotId)
    // Deleting the only version on the last page leaves that page empty.
    if (items.value.length === 0 && page.value > 1) {
      page.value -= 1
      await fetch(shotId)
    }
  }

  return {
    items,
    total,
    page,
    pageSize,
    isLoading,
    uploadState,
    uploadProgress,
    fetch,
    setPage,
    upload,
    remove,
  }
})
