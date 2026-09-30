import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

import type { FileStatus } from '../../lib/api'

type PaperFile = {
  id: string
  name: string
  status: FileStatus
  sizeBytes: number
}

type Chat = {
  id: string
  title: string
}

export type Folder = {
  id: string
  name: string
  files: PaperFile[]
  chats: Chat[]
}

type FoldersState = {
  folders: Folder[]
  selectedFolderId: string | null
  selectedChatId: string | null
  isCreatingFolder: boolean
  draftFolderName: string
}

const initialState: FoldersState = {
  folders: [],
  selectedFolderId: null,
  selectedChatId: null,
  isCreatingFolder: false,
  draftFolderName: '',
}

const foldersSlice = createSlice({
  name: 'folders',
  initialState,
  reducers: {
    startCreatingFolder(state) {
      state.isCreatingFolder = true
      state.draftFolderName = ''
    },
    cancelCreatingFolder(state) {
      state.isCreatingFolder = false
      state.draftFolderName = ''
    },
    setDraftFolderName(state, action: PayloadAction<string>) {
      state.draftFolderName = action.payload
    },
    createFolder(state) {
      const name = state.draftFolderName.trim()
      if (!name) {
        return
      }

      const folder: Folder = {
        id: `${name.toLowerCase().replaceAll(/\s+/g, '-')}-${Date.now()}`,
        name,
        files: [],
        chats: [],
      }

      state.folders.push(folder)
      state.selectedFolderId = folder.id
      state.selectedChatId = null
      state.isCreatingFolder = false
      state.draftFolderName = ''
    },
    folderCreated(
      state,
      action: PayloadAction<{
        id: string
        name: string
      }>,
    ) {
      const folder: Folder = {
        id: action.payload.id,
        name: action.payload.name,
        files: [],
        chats: [],
      }

      state.folders.push(folder)
      state.selectedFolderId = folder.id
      state.selectedChatId = null
      state.isCreatingFolder = false
      state.draftFolderName = ''
    },
    foldersLoaded(
      state,
      action: PayloadAction<
        {
          id: string
          name: string
        }[]
      >,
    ) {
      const existingFoldersById = new Map(
        state.folders.map((folder) => [folder.id, folder]),
      )
      state.folders = action.payload.map((folder) => ({
        id: folder.id,
        name: folder.name,
        files: existingFoldersById.get(folder.id)?.files ?? [],
        chats: existingFoldersById.get(folder.id)?.chats ?? [],
      }))

      if (
        state.selectedFolderId &&
        !state.folders.some((folder) => folder.id === state.selectedFolderId)
      ) {
        state.selectedFolderId = null
        state.selectedChatId = null
      }
    },
    folderFetched(
      state,
      action: PayloadAction<{
        id: string
        name: string
      }>,
    ) {
      const existingFolder = state.folders.find(
        (folder) => folder.id === action.payload.id,
      )

      if (existingFolder) {
        existingFolder.name = action.payload.name
      } else {
        state.folders.push({
          id: action.payload.id,
          name: action.payload.name,
          files: [],
          chats: [],
        })
      }

      state.selectedFolderId = action.payload.id
      state.selectedChatId = null
    },
    deleteFolder(state, action: PayloadAction<string>) {
      state.folders = state.folders.filter(
        (folder) => folder.id !== action.payload,
      )

      if (state.selectedFolderId === action.payload) {
        state.selectedFolderId = null
        state.selectedChatId = null
      }
    },
    selectFolder(state, action: PayloadAction<string>) {
      state.selectedFolderId = action.payload
      state.selectedChatId = null
    },
    createChat(state) {
      const folder = state.folders.find(
        (candidate) => candidate.id === state.selectedFolderId,
      )
      if (!folder) {
        return
      }

      const chat: Chat = {
        id: `chat-${Date.now()}`,
        title: `Chat ${folder.chats.length + 1}`,
      }

      folder.chats.push(chat)
      state.selectedChatId = chat.id
    },
    selectChat(state, action: PayloadAction<string>) {
      state.selectedChatId = action.payload
    },
    addUploadedFileToSelectedFolder(
      state,
      action: PayloadAction<{
        id: string
        name: string
        status: FileStatus
        sizeBytes: number
      }>,
    ) {
      const folder = state.folders.find(
        (candidate) => candidate.id === state.selectedFolderId,
      )
      if (!folder) {
        return
      }

      const existingFile = folder.files.find(
        (file) => file.id === action.payload.id,
      )
      if (existingFile) {
        existingFile.name = action.payload.name
        existingFile.status = action.payload.status
        return
      }

      folder.files.push(action.payload)
    },
    folderFilesLoaded(
      state,
      action: PayloadAction<{
        folderId: string
        files: {
          id: string
          name: string
          status: FileStatus
          sizeBytes: number
        }[]
      }>,
    ) {
      const folder = state.folders.find(
        (candidate) => candidate.id === action.payload.folderId,
      )
      if (!folder) {
        return
      }

      folder.files = action.payload.files
    },
  },
})

export const {
  addUploadedFileToSelectedFolder,
  cancelCreatingFolder,
  createChat,
  createFolder,
  deleteFolder,
  folderCreated,
  folderFetched,
  folderFilesLoaded,
  foldersLoaded,
  selectChat,
  selectFolder,
  setDraftFolderName,
  startCreatingFolder,
} = foldersSlice.actions

export default foldersSlice.reducer
