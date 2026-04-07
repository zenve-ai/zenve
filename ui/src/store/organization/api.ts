import { createApi } from '@reduxjs/toolkit/query/react'
import { createBaseQueryWithReauth } from '@/lib/api'
import config from '@/config'
import type { OrganizationIconKey, OrganizationSummary } from '@/types'

interface OrgWithRoleResponse {
  id: string
  name: string
  slug: string
  base_path: string
  created_at: string
  updated_at: string
  role: string
}

interface OrgCreatedResponse extends OrgWithRoleResponse {
  api_key: {
    id: string
    org_id: string
    name: string
    scopes: string
    is_active: boolean
    created_at: string
    expires_at: string | null
    raw_key: string
  }
}

const ICON_KEYS: OrganizationIconKey[] = ['zap', 'triangle', 'box', 'cpu', 'building', 'layers']

function assignIconKey(slug: string): OrganizationIconKey {
  let hash = 0
  for (let i = 0; i < slug.length; i++) {
    hash = (hash * 31 + slug.charCodeAt(i)) | 0
  }
  return ICON_KEYS[Math.abs(hash) % ICON_KEYS.length]
}

function toOrganizationSummary(org: OrgWithRoleResponse): OrganizationSummary {
  return {
    id: org.id,
    name: org.name,
    slug: org.slug,
    role: org.role,
    iconKey: assignIconKey(org.slug),
  }
}

export const organizationApi = createApi({
  reducerPath: 'organizationApi',
  baseQuery: createBaseQueryWithReauth(config.apiUrl),
  tagTypes: ['Organization'],
  endpoints: (builder) => ({
    listOrganizations: builder.query<OrganizationSummary[], void>({
      query: () => '/orgs',
      transformResponse: (response: OrgWithRoleResponse[]) => response.map(toOrganizationSummary),
      providesTags: ['Organization'],
    }),
    createOrganization: builder.mutation<OrganizationSummary & { apiKey: string }, { name: string; slug?: string }>({
      query: (body) => ({ url: '/orgs', method: 'POST', body }),
      transformResponse: (response: OrgCreatedResponse) => ({
        ...toOrganizationSummary(response),
        apiKey: response.api_key.raw_key,
      }),
      invalidatesTags: ['Organization'],
    }),
  }),
})

export const { useListOrganizationsQuery, useCreateOrganizationMutation } = organizationApi
