import { Navigate } from 'react-router'
import { useAppSelector } from '@/store/hooks'
import { useListProjectsQuery, selectCurrentProject } from '@/store/project'
import { ProjectLoading } from './project-loading'

/**
 * `/` is not a destination — only redirects. Mounted under PrivateRoute so guests
 * never see this; they are sent to /login first.
 */
export function RootPathRedirect() {
  const { isLoading, isFetching, isSuccess, isError, data } = useListProjectsQuery()
  const current = useAppSelector(selectCurrentProject)

  const waiting = isLoading || isFetching
  if (waiting) return <ProjectLoading />

  const empty = isError || (isSuccess && (!data || data.length === 0))
  if (empty) return <Navigate to="/no-project" replace />

  if (isSuccess && data && data.length > 0) {
    const slug = current?.slug ?? data[0]?.slug
    if (slug) return <Navigate to={`/${slug}`} replace />
  }

  return <ProjectLoading />
}
