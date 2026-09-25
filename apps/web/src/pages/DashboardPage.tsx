import { useAuth } from '@clerk/react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'

import { useAppDispatch, useAppSelector } from '../app/hooks'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { folderFetched, foldersLoaded } from '../features/folders/foldersSlice'
import { fetchFolderByIdRequest, fetchFoldersRequest } from '../lib/api'

export function DashboardPage() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const { getToken } = useAuth()
  const folders = useAppSelector((state) => state.folders.folders)
  const [isLoadingFolders, setIsLoadingFolders] = useState(true)
  const [openingFolderId, setOpeningFolderId] = useState<string | null>(null)
  const [folderError, setFolderError] = useState<string | null>(null)

  useEffect(() => {
    let isCancelled = false

    async function loadFolders() {
      setIsLoadingFolders(true)
      setFolderError(null)

      try {
        const token = await getToken()
        if (!token) {
          throw new Error('Clerk did not return a session token.')
        }

        const folderList = await fetchFoldersRequest(token)

        if (!isCancelled) {
          dispatch(foldersLoaded(folderList))
        }
      } catch (error) {
        if (!isCancelled) {
          setFolderError(
            error instanceof Error ? error.message : 'Unable to load folders.',
          )
        }
      } finally {
        if (!isCancelled) {
          setIsLoadingFolders(false)
        }
      }
    }

    void loadFolders()

    return () => {
      isCancelled = true
    }
  }, [dispatch, getToken])

  async function handleOpenFolder(folderId: string) {
    if (openingFolderId) {
      return
    }

    setFolderError(null)
    setOpeningFolderId(folderId)

    try {
      const token = await getToken()
      if (!token) {
        throw new Error('Clerk did not return a session token.')
      }

      const folder = await fetchFolderByIdRequest(token, folderId)
      dispatch(folderFetched(folder))
      navigate(`/folders/${folder.id}`)
    } catch (error) {
      setFolderError(
        error instanceof Error ? error.message : 'Unable to open folder.',
      )
    } finally {
      setOpeningFolderId(null)
    }
  }

  return (
    <section className="dashboard-page">
      <header className="dashboard-heading">
        <p className="eyebrow">Workspace</p>
        <h1>Dashboard</h1>
        <p>Open a folder to continue with its papers and chats.</p>
      </header>

      {folderError ? <p className="dashboard-error">{folderError}</p> : null}

      {isLoadingFolders ? (
        <div className="dashboard-empty-panel">
          <LoadingSpinner label="Loading folders..." />
        </div>
      ) : folders.length > 0 ? (
        <div className="dashboard-folder-grid" aria-label="Folders">
          {folders.map((folder) => (
            <button
              key={folder.id}
              type="button"
              className="dashboard-folder-card"
              disabled={openingFolderId === folder.id}
              onClick={() => void handleOpenFolder(folder.id)}
            >
              <span aria-hidden="true">▣</span>
              <strong>{folder.name}</strong>
              <small>
                {folder.files.length} files · {folder.chats.length} chats
              </small>
            </button>
          ))}
        </div>
      ) : (
        <div className="dashboard-empty-panel">
          <h2>No folders yet</h2>
          <p>Create a folder from the left menu to start organizing papers.</p>
        </div>
      )}
    </section>
  )
}
