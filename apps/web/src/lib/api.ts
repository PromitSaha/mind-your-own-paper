export const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export type CurrentUserResponse = {
  id: string
  clerk_user_id: string
  email: string
  first_name: string | null
  last_name: string | null
  image_url: string | null
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export type FolderResponse = {
  id: string
  owner_id: string
  name: string
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export type FileStatus =
  | 'PENDING_UPLOAD'
  | 'UPLOADED'
  | 'PROCESSING'
  | 'READY'
  | 'FAILED'

export type FileUploadInitiateResponse = {
  file_id: string
  filename: string
  status: FileStatus
  upload_url: string
  expires_in: number
}

export type FileUploadCompleteResponse = {
  file_id: string
  filename: string
  status: FileStatus
}

export type FileResponse = {
  id: string
  folder_id: string
  original_filename: string
  content_type: string
  size_bytes: number
  status: FileStatus
  is_deleted: boolean
  created_at: string
  updated_at: string
}

export type FileDownloadUrlResponse = {
  file_id: string
  download_url: string
  expires_in: number
}

export async function fetchCurrentUser(
  token: string,
): Promise<CurrentUserResponse> {
  const response = await fetch(`${apiBaseUrl}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Auth request failed with status ${response.status}`)
  }

  return response.json() as Promise<CurrentUserResponse>
}

export async function createFolderRequest(
  token: string,
  name: string,
): Promise<FolderResponse> {
  const response = await fetch(`${apiBaseUrl}/folders`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name }),
  })

  if (!response.ok) {
    throw new Error(`Create folder failed with status ${response.status}`)
  }

  return response.json() as Promise<FolderResponse>
}

export async function fetchFoldersRequest(
  token: string,
): Promise<FolderResponse[]> {
  const response = await fetch(`${apiBaseUrl}/folders`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Fetch folders failed with status ${response.status}`)
  }

  return response.json() as Promise<FolderResponse[]>
}

export async function fetchFolderByIdRequest(
  token: string,
  folderId: string,
): Promise<FolderResponse> {
  const response = await fetch(`${apiBaseUrl}/folders/${folderId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Fetch folder failed with status ${response.status}`)
  }

  return response.json() as Promise<FolderResponse>
}

export async function deleteFolderRequest(
  token: string,
  folderId: string,
): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/folders/${folderId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Delete folder failed with status ${response.status}`)
  }
}

export async function initiateFileUploadRequest(
  token: string,
  folderId: string,
  file: File,
): Promise<FileUploadInitiateResponse> {
  const response = await fetch(`${apiBaseUrl}/folders/${folderId}/files/uploads`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filename: file.name,
      content_type: 'application/pdf',
      size_bytes: file.size,
    }),
  })

  if (!response.ok) {
    throw new Error(`Initiate upload failed with status ${response.status}`)
  }

  return response.json() as Promise<FileUploadInitiateResponse>
}

export async function uploadFileToS3(
  uploadUrl: string,
  file: File,
): Promise<void> {
  const response = await fetch(uploadUrl, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/pdf',
    },
    body: file,
  })

  if (!response.ok) {
    throw new Error(`S3 upload failed with status ${response.status}`)
  }
}

export async function completeFileUploadRequest(
  token: string,
  fileId: string,
): Promise<FileUploadCompleteResponse> {
  const response = await fetch(`${apiBaseUrl}/files/${fileId}/complete`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Complete upload failed with status ${response.status}`)
  }

  return response.json() as Promise<FileUploadCompleteResponse>
}

export async function fetchFolderFilesRequest(
  token: string,
  folderId: string,
): Promise<FileResponse[]> {
  const response = await fetch(`${apiBaseUrl}/folders/${folderId}/files`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Fetch folder files failed with status ${response.status}`)
  }

  return response.json() as Promise<FileResponse[]>
}

export async function fetchFileDownloadUrlRequest(
  token: string,
  fileId: string,
): Promise<FileDownloadUrlResponse> {
  const response = await fetch(`${apiBaseUrl}/files/${fileId}/download-url`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Fetch file URL failed with status ${response.status}`)
  }

  return response.json() as Promise<FileDownloadUrlResponse>
}
