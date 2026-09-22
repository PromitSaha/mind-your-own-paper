import { createSlice } from '@reduxjs/toolkit'

type UiState = {
  isSidebarOpen: boolean
}

const initialState: UiState = {
  isSidebarOpen: true,
}

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar(state) {
      state.isSidebarOpen = !state.isSidebarOpen
    },
  },
})

export const { toggleSidebar } = uiSlice.actions
export default uiSlice.reducer
