import { configureStore } from '@reduxjs/toolkit'
import { authReducer, authApi } from './auth'
import { workspaceReducer, workspaceApi } from './workspace'
import { agentsApi } from './agents'
import { runsApi, runsReducer } from './runs'
import { wsReducer } from './ws'
import { runtimeApi } from './runtime'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    workspace: workspaceReducer,
    runs: runsReducer,
    ws: wsReducer,
    [authApi.reducerPath]: authApi.reducer,
    [workspaceApi.reducerPath]: workspaceApi.reducer,
    [agentsApi.reducerPath]: agentsApi.reducer,
    [runsApi.reducerPath]: runsApi.reducer,
    [runtimeApi.reducerPath]: runtimeApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(
      authApi.middleware,
      workspaceApi.middleware,
      agentsApi.middleware,
      runsApi.middleware,
      runtimeApi.middleware,
    ),
})

export type AppRootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
