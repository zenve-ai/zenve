import { configureStore } from '@reduxjs/toolkit'
import { authReducer, authApi } from './auth'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    [authApi.reducerPath]: authApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(authApi.middleware),
})

export type AppRootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
