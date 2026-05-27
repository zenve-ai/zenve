import { configureStore } from '@reduxjs/toolkit'
import { authReducer, authApi } from './auth'
import { workspaceReducer, workspaceApi } from './workspace'
import { agentsApi } from './agents'
import { runsApi, runsReducer } from './runs'
import { wsReducer } from './ws'
import { runtimeApi } from './runtime'
import { issuesApi } from './issues'
import { pullRequestsApi } from './pull-requests'
import { settingsApi } from './settings'

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
    [issuesApi.reducerPath]: issuesApi.reducer,
    [pullRequestsApi.reducerPath]: pullRequestsApi.reducer,
    [settingsApi.reducerPath]: settingsApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(
      authApi.middleware,
      workspaceApi.middleware,
      agentsApi.middleware,
      runsApi.middleware,
      runtimeApi.middleware,
      issuesApi.middleware,
      pullRequestsApi.middleware,
      settingsApi.middleware,
    ),
})

export type AppRootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
