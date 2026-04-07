import { Navigate } from 'react-router'
import { useAppSelector } from '@/store/hooks'
import { useListOrganizationsQuery, selectCurrentOrganization } from '@/store/organization'
import { OrgLoading } from './org-loading'

/**
 * `/` is not a destination — only redirects. Mounted under PrivateRoute so guests
 * never see this; they are sent to /login first.
 */
export function RootPathRedirect() {
  const { isLoading, isFetching, isSuccess, isError, data } = useListOrganizationsQuery()
  const current = useAppSelector(selectCurrentOrganization)

  const waiting = isLoading || isFetching
  if (waiting) return <OrgLoading />

  const empty = isError || (isSuccess && (!data || data.length === 0))
  if (empty) return <Navigate to="/no-organization" replace />

  if (isSuccess && data && data.length > 0) {
    const slug = current?.slug ?? data[0]?.slug
    if (slug) return <Navigate to={`/${slug}`} replace />
  }

  return <OrgLoading />
}
