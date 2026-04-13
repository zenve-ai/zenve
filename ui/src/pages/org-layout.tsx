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
  useListOrganizationsQuery,
  resolveOrgFromSlug,
  selectCurrentOrgId,
  selectOrganizations,
  setCurrentOrganization,
} from '@/store/organization'
import { useListAgentsQuery } from '@/store/agents'
import { selectWsStatus } from '@/store/ws'
import { useOrgWebSocket } from '@/hooks/use-org-websocket'
import { OrgLoading } from './org-loading'

export default function OrgLayout() {
  // --- declarations ---
  const { orgSlug } = useParams<{ orgSlug: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const { isLoading, isFetching, isSuccess, isError, data } = useListOrganizationsQuery()
  const organizations = useAppSelector(selectOrganizations)
  const currentOrgId = useAppSelector(selectCurrentOrgId)
  const { data: agents = [] } = useListAgentsQuery(
    { orgSlug: orgSlug! },
    { skip: !orgSlug },
  )
  const waiting = isLoading || isFetching
  const empty = isError || (isSuccess && (!data || data.length === 0))
  const base = orgSlug ? `/${orgSlug}` : ''
  const detailMatch = matchPath({ path: '/:orgSlug/agents/:agentSlug', end: true }, location.pathname)
  const listMatch = matchPath({ path: '/:orgSlug/agents', end: true }, location.pathname)
  const agent = detailMatch?.params.agentSlug
    ? agents.find((a) => a.slug === detailMatch.params.agentSlug)
    : undefined
  const wsStatus = useAppSelector(selectWsStatus)

  useOrgWebSocket(currentOrgId ?? '')

  // --- effects ---
  useEffect(() => {
    if (!isSuccess || !organizations.length || !orgSlug) return
    const match = resolveOrgFromSlug(organizations, orgSlug)
    if (match) {
      if (match.id !== currentOrgId) dispatch(setCurrentOrganization(match.id))
    } else {
      navigate(`/${organizations[0].slug}`, { replace: true })
    }
  }, [orgSlug, organizations, isSuccess, currentOrgId, dispatch, navigate])

  // --- render helpers ---
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
            <BreadcrumbItem className="hidden md:block">
              <BreadcrumbLink asChild>
                <Link to={base}>Dashboard</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator className="hidden md:block" />
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
      <SidebarInset>
        {renderHeader()}
        <Outlet />
      </SidebarInset>
    </SidebarProvider>
  )

  const renderMain = () => {
    if (waiting) return <OrgLoading />
    if (empty) return <Navigate to="/no-organization" replace />
    return renderContent()
  }

  // --- main render ---
  return renderMain()
}
