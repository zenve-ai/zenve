import { configureStore } from '@reduxjs/toolkit'
import { authReducer, authApi } from './auth'
import { projectReducer, projectApi } from './project'
import { agentsApi } from './agents'
import { runsApi, runsReducer } from './runs'
import { wsReducer } from './ws'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    project: projectReducer,
    runs: runsReducer,
    ws: wsReducer,
    [authApi.reducerPath]: authApi.reducer,
    [projectApi.reducerPath]: projectApi.reducer,
    [agentsApi.reducerPath]: agentsApi.reducer,
    [runsApi.reducerPath]: runsApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(
      authApi.middleware,
      projectApi.middleware,
      agentsApi.middleware,
      runsApi.middleware,
    ),
})

export type AppRootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
