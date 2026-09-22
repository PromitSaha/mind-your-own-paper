import { configureStore } from '@reduxjs/toolkit'

import foldersReducer from '../features/folders/foldersSlice'
import uiReducer from '../features/ui/uiSlice'

export const store = configureStore({
  reducer: {
    folders: foldersReducer,
    ui: uiReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
