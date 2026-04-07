import { Navigate } from 'react-router'
import { useAppSelector } from '@/store/hooks'
import { useListOrganizationsQuery, selectCurrentOrganization } from '@/store/organization'
import { OrgLoading } from './org-loading'

export function OrgRootRedirect() {
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
