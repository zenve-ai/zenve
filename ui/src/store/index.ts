import { configureStore } from '@reduxjs/toolkit'
import { authReducer, authApi } from './auth'
import { organizationReducer, organizationApi } from './organization'
import { agentsApi } from './agents'
import { runsApi, runsReducer } from './runs'
import { wsReducer } from './ws'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    organization: organizationReducer,
    runs: runsReducer,
    ws: wsReducer,
    [authApi.reducerPath]: authApi.reducer,
    [organizationApi.reducerPath]: organizationApi.reducer,
    [agentsApi.reducerPath]: agentsApi.reducer,
    [runsApi.reducerPath]: runsApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(
      authApi.middleware,
      organizationApi.middleware,
      agentsApi.middleware,
      runsApi.middleware,
    ),
})

export type AppRootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
