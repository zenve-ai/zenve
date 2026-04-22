import { Navigate } from 'react-router'
import { useAppSelector } from '@/store/hooks'
import { useListProjectsQuery, selectCurrentProject } from '@/store/project'
import { ProjectLoading } from './project-loading'

/**
 * Shown when the user has no projects. Placeholder until create-project is implemented.
 */
export default function NoProjectPage() {
  const { isLoading, isFetching, isSuccess, data } = useListProjectsQuery()
  const current = useAppSelector(selectCurrentProject)

  const waiting = isLoading || isFetching
  if (waiting) return <ProjectLoading />

  if (isSuccess && data && data.length > 0) {
    const slug = current?.slug ?? data[0].slug
    return <Navigate to={`/${slug}`} replace />
  }

  return <Navigate to="/onboarding" replace />
}
