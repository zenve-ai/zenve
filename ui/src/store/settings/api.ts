import { createApi } from '@reduxjs/toolkit/query/react'
import { createRuntimeBaseQuery } from '@/lib/api'
import config from '@/config'
import type { GlobalSettings } from '@/types'

export const settingsApi = createApi({
  reducerPath: 'settingsApi',
  baseQuery: createRuntimeBaseQuery(config.runtimeUrl),
  tagTypes: ['GlobalSettings'],
  endpoints: (builder) => ({
    getGlobalSettings: builder.query<GlobalSettings, void>({
      query: () => '/settings',
      providesTags: ['GlobalSettings'],
    }),
    updateGlobalSettings: builder.mutation<GlobalSettings, Partial<GlobalSettings>>({
      query: (body) => ({ url: '/settings', method: 'PATCH', body }),
      invalidatesTags: ['GlobalSettings'],
    }),
  }),
})

export const {
  useGetGlobalSettingsQuery,
  useUpdateGlobalSettingsMutation,
} = settingsApi
