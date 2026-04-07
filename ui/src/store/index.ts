import { configureStore } from '@reduxjs/toolkit'
import { authReducer, authApi } from './auth'
import { organizationReducer, organizationApi } from './organization'
import { agentsApi } from './agents'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    organization: organizationReducer,
    [authApi.reducerPath]: authApi.reducer,
    [organizationApi.reducerPath]: organizationApi.reducer,
    [agentsApi.reducerPath]: agentsApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(authApi.middleware, organizationApi.middleware, agentsApi.middleware),
})

export type AppRootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
