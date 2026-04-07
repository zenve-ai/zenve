import { fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { BaseQueryFn, FetchArgs, FetchBaseQueryError } from '@reduxjs/toolkit/query'
import { clearStoredAuth, clearCurrentUser } from '@/store/auth/slice'
import { getToken } from '@/lib/token'

export const createBaseQueryWithReauth = (
  baseUrl: string,
): BaseQueryFn<string | FetchArgs, unknown, FetchBaseQueryError> =>
  async (args, api, extraOptions) => {
    const result = await fetchBaseQuery({
      baseUrl,
      prepareHeaders: (headers) => {
        const token = getToken()
        if (token) headers.set('authorization', `Bearer ${token}`)
        return headers
      },
    })(args, api, extraOptions)

    if (result.error?.status === 401) {
      clearStoredAuth()
      api.dispatch(clearCurrentUser())
    }

    return result
  }
