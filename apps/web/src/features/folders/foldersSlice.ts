import { createSlice, type PayloadAction } from '@reduxjs/toolkit'

type PaperFile = {
  id: string
  name: string
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
    addFilesToSelectedFolder(state, action: PayloadAction<string[]>) {
      const folder = state.folders.find(
        (candidate) => candidate.id === state.selectedFolderId,
      )
      if (!folder) {
        return
      }

      folder.files.push(
        ...action.payload.map((name) => ({
          id: `file-${Date.now()}-${name}`,
          name,
        })),
      )
    },
  },
})

export const {
  addFilesToSelectedFolder,
  cancelCreatingFolder,
  createChat,
  createFolder,
  selectChat,
  selectFolder,
  setDraftFolderName,
  startCreatingFolder,
} = foldersSlice.actions

export default foldersSlice.reducer
