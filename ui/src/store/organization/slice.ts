import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import type { OrganizationSummary } from '@/types'
import { organizationApi } from './api'

const STORAGE_KEY = 'zenve-current-org-id'

function readStoredOrgId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function writeStoredOrgId(id: string) {
  try {
    localStorage.setItem(STORAGE_KEY, id)
  } catch {
    /* ignore */
  }
}

export function resolveOrgId(orgs: OrganizationSummary[], candidate: string | null): string {
  if (!orgs.length) return ''
  if (candidate && orgs.some((o) => o.id === candidate)) return candidate
  return orgs[0].id
}

export function resolveOrgFromSlug(
  orgs: OrganizationSummary[],
  slug: string | undefined,
): OrganizationSummary | null {
  if (!slug) return null
  return orgs.find((o) => o.slug === slug) ?? null
}

interface OrganizationState {
  organizations: OrganizationSummary[]
  currentOrgId: string
  isInitialized: boolean
  listLoaded: boolean
}

const initialState: OrganizationState = {
  organizations: [],
  currentOrgId: '',
  isInitialized: false,
  listLoaded: false,
}

export const organizationSlice = createSlice({
  name: 'organization',
  initialState,
  reducers: {
    setCurrentOrganization: (state, action: PayloadAction<string>) => {
      const id = resolveOrgId(state.organizations, action.payload)
      state.currentOrgId = id
      writeStoredOrgId(id)
    },
    restoreFromStorage: (state) => {
      const stored = readStoredOrgId()
      state.currentOrgId = stored ?? ''
      state.isInitialized = true
    },
  },
  extraReducers: (builder) => {
    builder.addMatcher(organizationApi.endpoints.listOrganizations.matchFulfilled, (state, { payload }) => {
      state.organizations = payload
      state.listLoaded = true
      const stored = state.currentOrgId || readStoredOrgId()
      const resolved = resolveOrgId(payload, stored)
      state.currentOrgId = resolved
      writeStoredOrgId(resolved)
    })
    builder.addMatcher(organizationApi.endpoints.listOrganizations.matchRejected, (state) => {
      state.organizations = []
      state.listLoaded = true
      state.currentOrgId = ''
      writeStoredOrgId('')
    })
  },
})

export const { setCurrentOrganization, restoreFromStorage } = organizationSlice.actions

export const selectOrganizations = (state: { organization: OrganizationState }) =>
  state.organization.organizations
export const selectCurrentOrgId = (state: { organization: OrganizationState }) =>
  state.organization.currentOrgId
export const selectCurrentOrganization = (state: { organization: OrganizationState }) => {
  const { organizations, currentOrgId } = state.organization
  return organizations.find((o) => o.id === currentOrgId) ?? organizations[0] ?? null
}
export const selectIsOrganizationInitialized = (state: { organization: OrganizationState }) =>
  state.organization.isInitialized
export const selectOrgListLoaded = (state: { organization: OrganizationState }) =>
  state.organization.listLoaded

export default organizationSlice.reducer
