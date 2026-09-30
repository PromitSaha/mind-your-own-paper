import { useAuth } from '@clerk/react'
import type { ChangeEvent } from 'react'
import { useEffect, useState } from 'react'
import { Navigate, useParams } from 'react-router'

import { useAppDispatch, useAppSelector } from '../app/hooks'
import { LoadingSpinner } from '../components/LoadingSpinner'
import {
  addUploadedFileToSelectedFolder,
  createChat,
  folderFetched,
  folderFilesLoaded,
  selectChat,
} from '../features/folders/foldersSlice'
import {
  completeFileUploadRequest,
  fetchFolderByIdRequest,
  fetchFolderFilesRequest,
  fetchFileDownloadUrlRequest,
  initiateFileUploadRequest,
  uploadFileToS3,
} from '../lib/api'

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`
  }

  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`
  }

  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`
}

export function FoldersPage() {
  const dispatch = useAppDispatch()
  const { getToken } = useAuth()
  const { folderId } = useParams<{ folderId: string }>()
  const { folders, selectedChatId, selectedFolderId } = useAppSelector(
    (state) => state.folders,
  )
  const [isLoadingFolder, setIsLoadingFolder] = useState(true)
  const [folderLoadError, setFolderLoadError] = useState<string | null>(null)
  const [fileLoadError, setFileLoadError] = useState<string | null>(null)
  const [isUploadingFiles, setIsUploadingFiles] = useState(false)
  const [openingFileId, setOpeningFileId] = useState<string | null>(null)
  const [uploadMessage, setUploadMessage] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const selectedFolder =
    folders.find((folder) => folder.id === (folderId ?? selectedFolderId)) ?? null
  const selectedChat =
    selectedFolder?.chats.find((chat) => chat.id === selectedChatId) ?? null

  useEffect(() => {
    if (!folderId) {
      return
    }

    const routeFolderId = folderId
    let isCancelled = false

    async function loadFolder() {
      setIsLoadingFolder(true)
      setFolderLoadError(null)
      setFileLoadError(null)

      try {
        const token = await getToken()
        if (!token) {
          throw new Error('Clerk did not return a session token.')
        }

        const folder = await fetchFolderByIdRequest(token, routeFolderId)
        const files = await fetchFolderFilesRequest(token, routeFolderId)

        if (!isCancelled) {
          dispatch(folderFetched({ id: folder.id, name: folder.name }))
          dispatch(
            folderFilesLoaded({
              folderId: folder.id,
              files: files.map((file) => ({
                id: file.id,
                name: file.original_filename,
                status: file.status,
                sizeBytes: file.size_bytes,
              })),
            }),
          )
        }
      } catch (error) {
        if (!isCancelled) {
          setFolderLoadError(
            error instanceof Error ? error.message : 'Unable to load folder.',
          )
          setFileLoadError('Unable to load files for this folder.')
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingFolder(false)
        }
      }
    }

    void loadFolder()

    return () => {
      isCancelled = true
    }
  }, [dispatch, folderId, getToken])

  async function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? [])
    event.target.value = ''

    if (!selectedFolder || selectedFiles.length === 0 || isUploadingFiles) {
      return
    }

    const nonPdfFile = selectedFiles.find(
      (file) => file.type !== 'application/pdf',
    )
    if (nonPdfFile) {
      setUploadMessage(null)
      setUploadError('Only PDF files can be uploaded.')
      return
    }

    setIsUploadingFiles(true)
    setUploadError(null)
    setUploadMessage(`Uploading ${selectedFiles.length} PDF file(s)...`)

    try {
      const token = await getToken()
      if (!token) {
        throw new Error('Clerk did not return a session token.')
      }

      for (const file of selectedFiles) {
        setUploadMessage(`Preparing ${file.name}...`)
        const upload = await initiateFileUploadRequest(
          token,
          selectedFolder.id,
          file,
        )

        setUploadMessage(`Uploading ${file.name} to S3...`)
        await uploadFileToS3(upload.upload_url, file)

        setUploadMessage(`Verifying ${file.name}...`)
        const completedFile = await completeFileUploadRequest(
          token,
          upload.file_id,
        )

        dispatch(
          addUploadedFileToSelectedFolder({
            id: completedFile.file_id,
            name: completedFile.filename,
            status: completedFile.status,
            sizeBytes: file.size,
          }),
        )
      }

      setUploadMessage('Upload complete.')
    } catch (error) {
      setUploadMessage(null)
      setUploadError(
        error instanceof Error ? error.message : 'Unable to upload PDF.',
      )
    } finally {
      setIsUploadingFiles(false)
    }
  }

  async function handleOpenPdf(fileId: string) {
    if (openingFileId) {
      return
    }

    const pdfWindow = window.open('', '_blank')
    if (!pdfWindow) {
      setUploadError('Your browser blocked the PDF window.')
      return
    }

    pdfWindow.opener = null
    setOpeningFileId(fileId)
    setUploadError(null)

    try {
      const token = await getToken()
      if (!token) {
        throw new Error('Clerk did not return a session token.')
      }

      const { download_url: downloadUrl } = await fetchFileDownloadUrlRequest(
        token,
        fileId,
      )
      pdfWindow.location.href = downloadUrl
    } catch (error) {
      pdfWindow.close()
      setUploadError(
        error instanceof Error ? error.message : 'Unable to open PDF.',
      )
    } finally {
      setOpeningFileId(null)
    }
  }

  if (!folderId) {
    return <Navigate to="/dashboard" replace />
  }

  if (isLoadingFolder) {
    return (
      <section className="folder-blank-page">
        <div>
          <LoadingSpinner label="Loading folder..." />
        </div>
      </section>
    )
  }

  if (folderLoadError) {
    return (
      <section className="folder-blank-page">
        <div>
          <h1>Folder unavailable</h1>
          <p>{folderLoadError}</p>
        </div>
      </section>
    )
  }

  if (!selectedFolder) {
    return (
      <section className="folder-blank-page">
        <div>
          <h1>Folders</h1>
          <p>
            Create a folder from the left menu to group PDFs and chats around a
            research topic.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="folder-simple-page">
      <header className="folder-simple-header">
        <h1>{selectedFolder.name}</h1>
        <p>
          {selectedFolder.files.length} files · {selectedFolder.chats.length}{' '}
          chats
        </p>
      </header>

      <section className="folder-files-board" aria-label="Folder PDF files">
        <div className="folder-section-header">
          <h2>Files</h2>
          <label className="secondary-button file-upload-button">
            {isUploadingFiles ? 'Uploading' : 'Upload PDFs'}
            <input
              type="file"
              accept="application/pdf"
              multiple
              disabled={isUploadingFiles}
              onChange={handleFileUpload}
            />
          </label>
        </div>

        {isUploadingFiles ? (
          <LoadingSpinner label={uploadMessage ?? 'Uploading PDFs...'} />
        ) : uploadMessage ? (
          <p className="folder-upload-message">{uploadMessage}</p>
        ) : null}

        {uploadError ? (
          <p className="folder-upload-error">{uploadError}</p>
        ) : null}

        {fileLoadError ? (
          <p className="folder-upload-error">{fileLoadError}</p>
        ) : null}

        {selectedFolder.files.length > 0 ? (
          <div className="folder-file-grid">
            {selectedFolder.files.slice(0, 11).map((file) => (
              <button
                type="button"
                className="folder-file-tile"
                key={file.id}
                disabled={openingFileId === file.id}
                onClick={() => void handleOpenPdf(file.id)}
              >
                <span aria-hidden="true">PDF</span>
                <strong>{file.name}</strong>
                <small>
                  {file.status} · {formatFileSize(file.sizeBytes)}
                </small>
              </button>
            ))}
            {selectedFolder.files.length > 11 ? (
              <button type="button" className="folder-file-tile folder-file-more">
                More
              </button>
            ) : null}
          </div>
        ) : (
          <div className="folder-inline-empty">
            <p>No PDFs uploaded yet.</p>
          </div>
        )}
      </section>

      <section className="folder-chats-board" aria-label="Folder chats">
        <div className="folder-section-header">
          <h2>Chats</h2>
          <button
            type="button"
            className="secondary-button"
            onClick={() => dispatch(createChat())}
          >
            Create chat
          </button>
        </div>

        {selectedFolder.chats.length > 0 ? (
          <div className="folder-chat-list-simple">
            {selectedFolder.chats.map((chat) => (
              <button
                key={chat.id}
                type="button"
                className={
                  chat.id === selectedChat?.id
                    ? 'simple-chat-row simple-chat-row--active'
                    : 'simple-chat-row'
                }
                onClick={() => dispatch(selectChat(chat.id))}
              >
                <span>{chat.title}</span>
                <small>Uses this folder's PDFs</small>
              </button>
            ))}
          </div>
        ) : (
          <div className="folder-inline-empty">
            <p>No chats yet.</p>
          </div>
        )}
      </section>
    </section>
  )
}
