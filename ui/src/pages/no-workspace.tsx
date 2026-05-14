import { Navigate } from 'react-router'
import { useAppSelector } from '@/store/hooks'
import { useListWorkspacesQuery, selectCurrentWorkspace } from '@/store/workspace'
import { WorkspaceLoading } from './workspace-loading'

export default function NoWorkspacePage() {
  const { isLoading, isFetching, isSuccess, data } = useListWorkspacesQuery()
  const current = useAppSelector(selectCurrentWorkspace)

  const waiting = isLoading || isFetching
  if (waiting) return <WorkspaceLoading />

  if (isSuccess && data && data.length > 0) {
    const id = current?.id ?? data[0].id
    return <Navigate to={`/${id}`} replace />
  }

  return <Navigate to="/onboarding" replace />
}
