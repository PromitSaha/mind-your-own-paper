import type { ChangeEvent } from 'react'

import { useAppDispatch, useAppSelector } from '../app/hooks'
import {
  addFilesToSelectedFolder,
  createChat,
  selectChat,
} from '../features/folders/foldersSlice'

export function FoldersPage() {
  const dispatch = useAppDispatch()
  const { folders, selectedChatId, selectedFolderId } = useAppSelector(
    (state) => state.folders,
  )
  const selectedFolder =
    folders.find((folder) => folder.id === selectedFolderId) ?? null
  const selectedChat =
    selectedFolder?.chats.find((chat) => chat.id === selectedChatId) ?? null

  function handleFileUpload(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
      .filter((file) => file.type === 'application/pdf')
      .map((file) => file.name)

    if (files.length > 0) {
      dispatch(addFilesToSelectedFolder(files))
      event.target.value = ''
    }
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
            Upload PDFs
            <input
              type="file"
              accept="application/pdf"
              multiple
              onChange={handleFileUpload}
            />
          </label>
        </div>

        {selectedFolder.files.length > 0 ? (
          <div className="folder-file-grid">
            {selectedFolder.files.slice(0, 11).map((file) => (
              <div className="folder-file-tile" key={file.id}>
                <span aria-hidden="true">PDF</span>
                <strong>{file.name}</strong>
              </div>
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

        <div className="folder-chat-workspace">
          <aside className="folder-chat-sidebar">
            {selectedFolder.chats.length > 0 ? (
              selectedFolder.chats.map((chat) => (
                <button
                  key={chat.id}
                  type="button"
                  className={
                    chat.id === selectedChatId
                      ? 'simple-chat-button simple-chat-button--active'
                      : 'simple-chat-button'
                  }
                  onClick={() => dispatch(selectChat(chat.id))}
                >
                  {chat.title}
                </button>
              ))
            ) : (
              <p>No chats yet.</p>
            )}
          </aside>

          <article className="simple-chat-preview">
            {selectedChat ? (
              <>
                <h3>{selectedChat.title}</h3>
                <p>
                  This chat will use the PDFs uploaded to {selectedFolder.name}.
                </p>
                <div className="simple-chat-composer">
                  <input placeholder="Ask about this folder..." />
                  <button type="button" className="primary-button">
                    Send
                  </button>
                </div>
              </>
            ) : (
              <div className="folder-inline-empty">
                <p>Create or select a chat to start asking about this folder.</p>
              </div>
            )}
          </article>
        </div>
      </section>
    </section>
  )
}
