import { useEffect } from 'react'
import { Link, matchPath, Navigate, Outlet, useLocation, useNavigate, useParams } from 'react-router'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/layout'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import {
  useListWorkspacesQuery,
  resolveWorkspaceFromId,
  selectCurrentWorkspaceId,
  selectWorkspaces,
  setCurrentWorkspace,
} from '@/store/workspace'
import { useListAgentsQuery } from '@/store/agents'
import { selectWsStatus } from '@/store/ws'
import { useWorkspaceWebSocket } from '@/hooks/use-workspace-websocket'
import { WorkspaceLoading } from './workspace-loading'

export default function WorkspaceLayout() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { isLoading, isFetching, isSuccess, isError, data } = useListWorkspacesQuery()
  const workspaces = useAppSelector(selectWorkspaces)
  const currentWorkspaceId = useAppSelector(selectCurrentWorkspaceId)
  const { data: agents = [] } = useListAgentsQuery(
    { workspaceId: workspaceId! },
    { skip: !workspaceId },
  )
  const waiting = isLoading || isFetching
  const empty = isError || (isSuccess && (!data || data.length === 0))
  const base = workspaceId ? `/${workspaceId}` : ''
  const detailMatch = matchPath({ path: '/:workspaceId/agents/:agentSlug', end: true }, location.pathname)
  const listMatch = matchPath({ path: '/:workspaceId/agents', end: true }, location.pathname)
  const issuesListMatch = matchPath({ path: '/:workspaceId/issues', end: true }, location.pathname)
  const issueDetailMatch = matchPath({ path: '/:workspaceId/issues/:issueId', end: true }, location.pathname)
  const settingsMatch = matchPath({ path: '/:workspaceId/settings/*' }, location.pathname)
  const agent = detailMatch?.params.agentSlug
    ? agents.find((a) => a.slug === detailMatch.params.agentSlug)
    : undefined
  const wsStatus = useAppSelector(selectWsStatus)

  useWorkspaceWebSocket(currentWorkspaceId ?? '')

  useEffect(() => {
    if (!isSuccess || !workspaces.length || !workspaceId) return
    const match = resolveWorkspaceFromId(workspaces, workspaceId)
    if (match) {
      if (match.id !== currentWorkspaceId) dispatch(setCurrentWorkspace(match.id))
    } else {
      navigate(`/${workspaces[0].id}`, { replace: true })
    }
  }, [workspaceId, workspaces, isSuccess, currentWorkspaceId, dispatch, navigate])

  const renderBreadcrumbTrail = () => {
    if (listMatch || detailMatch) {
      return (
        <>
          <BreadcrumbItem className="hidden md:block">
            <BreadcrumbLink asChild>
              <Link to={`${base}/agents`}>Agents</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          {detailMatch ? (
            <>
              <BreadcrumbSeparator className="hidden md:block" />
              <BreadcrumbItem>
                <BreadcrumbPage>{agent?.name ?? detailMatch.params.agentSlug}</BreadcrumbPage>
              </BreadcrumbItem>
            </>
          ) : (
            <>
              <BreadcrumbSeparator className="hidden md:block" />
              <BreadcrumbItem>
                <BreadcrumbPage>All agents</BreadcrumbPage>
              </BreadcrumbItem>
            </>
          )}
        </>
      )
    }

    if (issuesListMatch || issueDetailMatch) {
      return (
        <>
          <BreadcrumbItem className="hidden md:block">
            <BreadcrumbLink asChild>
              <Link to={`${base}/issues`}>Issues</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          {issueDetailMatch && (
            <>
              <BreadcrumbSeparator className="hidden md:block" />
              <BreadcrumbItem>
                <BreadcrumbPage>#{issueDetailMatch.params.issueId}</BreadcrumbPage>
              </BreadcrumbItem>
            </>
          )}
          {issuesListMatch && (
            <>
              <BreadcrumbSeparator className="hidden md:block" />
              <BreadcrumbItem>
                <BreadcrumbPage>All issues</BreadcrumbPage>
              </BreadcrumbItem>
            </>
          )}
        </>
      )
    }

    if (settingsMatch) {
      const section = location.pathname.split('/settings/')[1]
      const label = section
        ? section.charAt(0).toUpperCase() + section.slice(1)
        : 'Settings'
      return (
        <>
          <BreadcrumbItem className="hidden md:block">
            <BreadcrumbLink asChild>
              <Link to={`${base}/settings`}>Settings</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          {section && (
            <>
              <BreadcrumbSeparator className="hidden md:block" />
              <BreadcrumbItem>
                <BreadcrumbPage>{label}</BreadcrumbPage>
              </BreadcrumbItem>
            </>
          )}
        </>
      )
    }

    return (
      <BreadcrumbItem>
        <BreadcrumbPage>Overview</BreadcrumbPage>
      </BreadcrumbItem>
    )
  }

  const renderWsStatusDot = () => {
    if (wsStatus === 'idle') return null
    const dotClass = {
      connecting: 'bg-gray-400 animate-pulse',
      connected: 'bg-green-500',
      reconnecting: 'bg-amber-400 animate-pulse',
      failed: 'bg-red-500',
    }[wsStatus]
    const title = {
      connecting: 'Connecting…',
      connected: 'Connected',
      reconnecting: 'Reconnecting…',
      failed: 'Connection failed',
    }[wsStatus]
    return <span className={`size-2 rounded-full ${dotClass}`} title={title} />
  }

  const renderHeader = () => (
    <header className="flex h-12 shrink-0 items-center gap-2 border-b border-dashed border-border/60">
      <div className="flex flex-1 items-center gap-2 px-4">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="mr-2 data-[orientation=vertical]:h-4" />
        <Breadcrumb>
          <BreadcrumbList>
            {renderBreadcrumbTrail()}
          </BreadcrumbList>
        </Breadcrumb>
        <div className="ml-auto flex items-center pr-2">
          {renderWsStatusDot()}
        </div>
      </div>
    </header>
  )

  const renderContent = () => (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="h-[calc(100vh-1rem)]">
        {renderHeader()}
        <div className="flex-1 overflow-y-auto min-h-0">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  )

  const renderMain = () => {
    if (waiting) return <WorkspaceLoading />
    if (empty) return <Navigate to="/no-workspace" replace />
    return renderContent()
  }

  return renderMain()
}
