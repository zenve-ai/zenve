import { Navigate } from 'react-router'
import { useAppSelector } from '@/store/hooks'
import { useListOrganizationsQuery, selectCurrentOrganization } from '@/store/organization'
import { OrgLoading } from './org-loading'

/**
 * Shown when the user has no organizations. Placeholder until create-organization is implemented.
 */
export default function NoOrganizationPage() {
  const { isLoading, isFetching, isSuccess, data } = useListOrganizationsQuery()
  const current = useAppSelector(selectCurrentOrganization)

  const waiting = isLoading || isFetching
  if (waiting) return <OrgLoading />

  if (isSuccess && data && data.length > 0) {
    const slug = current?.slug ?? data[0].slug
    return <Navigate to={`/${slug}`} replace />
  }

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 bg-background px-6 text-center">
      <h1 className="text-xl font-semibold text-foreground">No organization yet</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        You are not a member of any organization. A create-organization workflow will be available
        here soon.
      </p>
    </div>
  )
}
