import { useClerk, useUser } from '@clerk/react'
import type { CSSProperties, FormEvent, KeyboardEvent, PointerEvent } from 'react'
import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router'

import { useAppDispatch, useAppSelector } from '../../app/hooks'
import {
  cancelCreatingFolder,
  createFolder,
  selectFolder,
  setDraftFolderName,
  startCreatingFolder,
} from '../../features/folders/foldersSlice'
import { toggleSidebar } from '../../features/ui/uiSlice'

const navigationItems = [
  { icon: '⌂', label: 'Dashboard', to: '/dashboard' },
  { icon: '▣', label: 'Folders', to: '/folders' },
]

export function AppLayout() {
  const dispatch = useAppDispatch()
  const isSidebarOpen = useAppSelector((state) => state.ui.isSidebarOpen)
  const folders = useAppSelector((state) => state.folders.folders)
  const selectedFolderId = useAppSelector(
    (state) => state.folders.selectedFolderId,
  )
  const isCreatingFolder = useAppSelector(
    (state) => state.folders.isCreatingFolder,
  )
  const draftFolderName = useAppSelector(
    (state) => state.folders.draftFolderName,
  )
  const navigate = useNavigate()
  const { signOut } = useClerk()
  const { user } = useUser()
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(220)

  const displayName =
    user?.fullName ?? user?.primaryEmailAddress?.emailAddress ?? 'User'
  const avatarUrl = user?.imageUrl
  const shellStyle = {
    '--sidebar-width': `${sidebarWidth}px`,
  } as CSSProperties

  async function handleLogout() {
    await signOut()
    setIsAccountModalOpen(false)
    navigate('/login', { replace: true })
  }

  function handleOpenSettings() {
    setIsAccountModalOpen(false)
    navigate('/settings')
  }

  function handleCreateFolder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    dispatch(createFolder())
    navigate('/folders')
  }

  function handleSelectFolder(folderId: string) {
    dispatch(selectFolder(folderId))
    navigate('/folders')
  }

  function handleResizeStart(event: PointerEvent<HTMLDivElement>) {
    event.preventDefault()
    const startX = event.clientX
    const startWidth = sidebarWidth

    function handlePointerMove(moveEvent: globalThis.PointerEvent) {
      const nextWidth = startWidth + moveEvent.clientX - startX
      setSidebarWidth(Math.min(Math.max(nextWidth, 184), 340))
    }

    function handlePointerUp() {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
  }

  function handleResizeKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      setSidebarWidth((currentWidth) => Math.max(currentWidth - 12, 184))
    }

    if (event.key === 'ArrowRight') {
      event.preventDefault()
      setSidebarWidth((currentWidth) => Math.min(currentWidth + 12, 340))
    }
  }

  return (
    <div
      className="app-shell"
      data-sidebar-open={isSidebarOpen}
      style={shellStyle}
    >
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>PaperMind</span>
        </div>

        <nav className="nav-list">
          {navigationItems.map((item) =>
            item.label === 'Folders' ? (
              <div className="sidebar-folders-block" key={item.to}>
                <div className="sidebar-folders-nav-row">
                  <NavLink
                    to={item.to}
                    className={({ isActive }) =>
                      isActive ? 'nav-link nav-link--active' : 'nav-link'
                    }
                  >
                    <span aria-hidden="true">{item.icon}</span>
                    {item.label}
                  </NavLink>
                  <button
                    type="button"
                    className="folder-create-icon-button"
                    aria-label="Create folder"
                    onClick={() => dispatch(startCreatingFolder())}
                  >
                    +
                  </button>
                </div>

                {isCreatingFolder ? (
                  <form
                    className="sidebar-create-folder-form"
                    onSubmit={handleCreateFolder}
                  >
                    <input
                      value={draftFolderName}
                      onChange={(event) =>
                        dispatch(setDraftFolderName(event.target.value))
                      }
                      placeholder="Folder name"
                      autoFocus
                    />
                    <div>
                      <button type="submit">Create</button>
                      <button
                        type="button"
                        onClick={() => dispatch(cancelCreatingFolder())}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                ) : null}

                {folders.length > 0 ? (
                  <div className="sidebar-folder-list">
                    {folders.map((folder) => (
                      <button
                        key={folder.id}
                        type="button"
                        className={
                          folder.id === selectedFolderId
                            ? 'sidebar-folder-button sidebar-folder-button--active'
                            : 'sidebar-folder-button'
                        }
                        onClick={() => handleSelectFolder(folder.id)}
                      >
                        {folder.name}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  isActive ? 'nav-link nav-link--active' : 'nav-link'
                }
              >
                <span aria-hidden="true">{item.icon}</span>
                {item.label}
              </NavLink>
            ),
          )}
        </nav>

        <button
          type="button"
          className="account-button"
          onClick={() => setIsAccountModalOpen(true)}
          aria-label="Open account menu"
        >
          {avatarUrl ? (
            <img src={avatarUrl} alt="" />
          ) : (
            <span className="account-fallback" aria-hidden="true">
              {displayName.slice(0, 1).toUpperCase()}
            </span>
          )}
          <span className="account-copy">
            <strong>{displayName}</strong>
            <span>Account</span>
          </span>
        </button>
      </aside>

      <div
        className="sidebar-resize-handle"
        role="separator"
        aria-label="Resize sidebar"
        aria-orientation="vertical"
        aria-valuemin={184}
        aria-valuemax={340}
        aria-valuenow={sidebarWidth}
        tabIndex={0}
        onPointerDown={handleResizeStart}
        onKeyDown={handleResizeKeyDown}
      />

      <div className="main-region">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="icon-button"
              onClick={() => dispatch(toggleSidebar())}
              aria-label="Toggle sidebar"
            >
              <span aria-hidden="true" />
            </button>
            <span className="topbar-divider" />
            <p>Read Deeper. Think Further.</p>
          </div>

          <div className="auth-actions">
            <span className="workspace-label">Modern research workspace</span>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>

      {isAccountModalOpen ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={() => setIsAccountModalOpen(false)}
        >
          <section
            className="account-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="account-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="account-modal-header">
              {avatarUrl ? (
                <img src={avatarUrl} alt="" />
              ) : (
                <span className="account-fallback" aria-hidden="true">
                  {displayName.slice(0, 1).toUpperCase()}
                </span>
              )}
              <div>
                <h2 id="account-modal-title">{displayName}</h2>
                <p>{user?.primaryEmailAddress?.emailAddress}</p>
              </div>
            </div>

            <div className="account-modal-actions">
              <button
                type="button"
                className="modal-action"
                onClick={handleOpenSettings}
              >
                User settings
              </button>
              <button
                type="button"
                className="modal-action modal-action--danger"
                onClick={handleLogout}
              >
                Log out
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  )
}
