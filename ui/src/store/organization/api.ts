import { createApi } from '@reduxjs/toolkit/query/react'
import { createBaseQueryWithReauth } from '@/lib/api'
import { MOCK_ORGANIZATIONS } from '@/lib/constants/organizations'
import config from '@/config'
import type { OrganizationSummary } from '@/types'

/** Simulated latency so loading UI can be verified (ms). */
const MOCK_ORG_LIST_DELAY_MS = 350

export const organizationApi = createApi({
  reducerPath: 'organizationApi',
  baseQuery: createBaseQueryWithReauth(config.apiUrl),
  tagTypes: ['Organization'],
  endpoints: (builder) => ({
    listOrganizations: builder.query<OrganizationSummary[], void>({
      async queryFn() {
        await new Promise((r) => setTimeout(r, MOCK_ORG_LIST_DELAY_MS))
        const empty = import.meta.env.VITE_ORGS_EMPTY === 'true'
        if (empty) return { data: [] as OrganizationSummary[] }
        return { data: MOCK_ORGANIZATIONS }
      },
    }),
  }),
})

export const { useListOrganizationsQuery } = organizationApi
