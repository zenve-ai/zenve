import { createApi } from '@reduxjs/toolkit/query/react'
import type { User, LoginData, SignupData } from '@/types'
import { setCurrentUser, clearCurrentUser } from './slice'
import { createBaseQueryWithReauth } from '@/lib/api'
import { setToken, setUserData, clearAuthData } from '@/lib/token'
import config from '@/config'

interface AuthResponse { access_token: string; user: User }

export const authApi = createApi({
  reducerPath: 'authApi',
  baseQuery: createBaseQueryWithReauth(config.apiUrl),
  endpoints: (builder) => ({
    login: builder.mutation<AuthResponse, LoginData>({
      query: (body) => ({ url: '/auth/login', method: 'POST', body }),
      async onQueryStarted(_, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled
          setToken(data.access_token)
          setUserData(data.user)
          dispatch(setCurrentUser(data.user))
        } catch {
          // Request failed or was aborted; leave auth state unchanged
        }
      },
    }),
    signup: builder.mutation<AuthResponse, SignupData>({
      query: (body) => ({ url: '/auth/signup', method: 'POST', body }),
      async onQueryStarted(_, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled
          setToken(data.access_token)
          setUserData(data.user)
          dispatch(setCurrentUser(data.user))
        } catch {
          // Request failed or was aborted; leave auth state unchanged
        }
      },
    }),
    me: builder.query<User, void>({
      query: () => ({ url: '/auth/me', method: 'GET' }),
      async onQueryStarted(_, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled
          setUserData(data)
          dispatch(setCurrentUser(data))
        } catch {
          // token may be invalid
        }
      },
    }),
    logout: builder.mutation<void, void>({
      query: () => ({ url: '/auth/logout', method: 'POST' }),
      async onQueryStarted(_, { dispatch, queryFulfilled }) {
        clearAuthData()
        dispatch(clearCurrentUser())
        try {
          await queryFulfilled
        } catch {
          // Logout request may fail after local session was cleared
        }
      },
    }),
  }),
})

export const { useLoginMutation, useSignupMutation, useLogoutMutation, useMeQuery } = authApi
