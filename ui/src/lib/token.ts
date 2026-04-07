import config from '@/config'

const TOKEN_KEY = config.tokenKey
const USER_KEY = config.userKey

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token)
export const removeToken = () => localStorage.removeItem(TOKEN_KEY)

export const getUserData = (): unknown => {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || '') } catch { return null }
}
export const setUserData = (user: unknown) => localStorage.setItem(USER_KEY, JSON.stringify(user))
export const removeUserData = () => localStorage.removeItem(USER_KEY)

export const clearAuthData = () => { removeToken(); removeUserData() }

export const isTokenExpired = (token = getToken()): boolean => {
  if (!token) return true
  try {
    const { exp } = JSON.parse(atob(token.split('.')[1])) as { exp?: number }
    return exp ? exp < Math.floor(Date.now() / 1000) : false
  } catch { return true }
}
