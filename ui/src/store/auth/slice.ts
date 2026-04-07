import { createSlice } from '@reduxjs/toolkit'
import type { User } from '@/types'
import { getToken, getUserData, clearAuthData, isTokenExpired } from '@/lib/token'

export const clearStoredAuth = clearAuthData

interface AuthState {
  current: User | null
  isAuthenticated: boolean
  isInitialized: boolean
}

export const authSlice = createSlice({
  name: 'auth',
  initialState: { current: null, isAuthenticated: false, isInitialized: false } as AuthState,
  reducers: {
    setCurrentUser: (state, action) => {
      state.current = action.payload
      state.isAuthenticated = true
      state.isInitialized = true
    },
    clearCurrentUser: (state) => {
      state.current = null
      state.isAuthenticated = false
      state.isInitialized = true
    },
    restoreFromStorage: (state) => {
      const token = getToken()
      const user = getUserData()
      if (token && user && !isTokenExpired(token)) {
        state.current = user as User
        state.isAuthenticated = true
      } else {
        clearAuthData()
      }
      state.isInitialized = true
    },
  },
})

export const { setCurrentUser, clearCurrentUser, restoreFromStorage } = authSlice.actions

export const selectCurrentUser = (state: { auth: AuthState }) => state.auth.current
export const selectIsAuthenticated = (state: { auth: AuthState }) => state.auth.isAuthenticated
export const selectIsInitialized = (state: { auth: AuthState }) => state.auth.isInitialized

export default authSlice.reducer
