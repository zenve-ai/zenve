import { createApi } from '@reduxjs/toolkit/query/react'
import { createRuntimeBaseQuery } from '@/lib/api'
import config from '@/config'
import type { AdapterItem, RuntimeInfo } from '@/types'

interface RuntimeInfoResponse {
  version: string
  status: string
  uptime_seconds: number
  pid: number
}

interface AdapterItemResponse {
  type: string
  name: string
  healthy: boolean
  default_model: string
}

export const runtimeApi = createApi({
  reducerPath: 'runtimeApi',
  baseQuery: createRuntimeBaseQuery(config.runtimeUrl),
  endpoints: (builder) => ({
    getRuntimeInfo: builder.query<RuntimeInfo, void>({
      query: () => '/runtime/info',
      transformResponse: (r: RuntimeInfoResponse): RuntimeInfo => ({
        version: r.version,
        status: r.status,
        uptimeSeconds: r.uptime_seconds,
        pid: r.pid,
      }),
    }),
    listAdapters: builder.query<AdapterItem[], void>({
      query: () => '/runtime/adapters',
      transformResponse: (r: AdapterItemResponse[]): AdapterItem[] =>
        r.map((a) => ({
          type: a.type,
          name: a.name,
          healthy: a.healthy,
          defaultModel: a.default_model,
        })),
    }),
  }),
})

export const { useGetRuntimeInfoQuery, useListAdaptersQuery } = runtimeApi
