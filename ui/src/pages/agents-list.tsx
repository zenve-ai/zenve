import { useState } from 'react'
import { useParams } from 'react-router'
import { Bot, LayoutGrid, LayoutList, Loader2, Play, Plus, Search } from 'lucide-react'
import { AgentCard, AgentRow } from '@/components/agents'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { useListAgentsQuery } from '@/store/agents'
import { useCreateRunMutation, useGetActiveRunQuery } from '@/store/runs'
import { cn } from '@/lib/utils'
import type { Agent } from '@/types'

type ViewMode = 'list' | 'cards'
type StatusFilter = 'all' | 'online' | 'unstable' | 'offline'

function agentStatusGroup(agent: Agent): StatusFilter {
  if (agent.status === 'active') return 'online'
  if (agent.status === 'paused' || agent.status === 'error') return 'unstable'
  return 'offline'
}

export default function AgentsList() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const base = workspaceId ? `/${workspaceId}` : ''
  const [view, setView] = useState<ViewMode>('list')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  const { data: agents = [], isLoading } = useListAgentsQuery(
    { workspaceId: workspaceId! },
    { skip: !workspaceId },
  )

  const { data: activeRun } = useGetActiveRunQuery(
    { workspaceId: workspaceId! },
    { skip: !workspaceId },
  )
  const [triggerRun, { isLoading: isStarting }] = useCreateRunMutation()

  const isRunning = !!activeRun || isStarting

  const onlineCount   = agents.filter((a) => agentStatusGroup(a) === 'online').length
  const unstableCount = agents.filter((a) => agentStatusGroup(a) === 'unstable').length
  const offlineCount  = agents.filter((a) => agentStatusGroup(a) === 'offline').length

  const filtered = agents.filter((a) => {
    const matchesSearch =
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.slug.toLowerCase().includes(search.toLowerCase()) ||
      a.adapterType?.toLowerCase().includes(search.toLowerCase())
    const matchesStatus =
      statusFilter === 'all' || agentStatusGroup(a) === statusFilter
    return matchesSearch && matchesStatus
  })

  const renderStatusChip = (value: StatusFilter, label: string, count: number, dotClass?: string) => (
    <button
      key={value}
      onClick={() => setStatusFilter(value)}
      className={cn(
        'flex items-center gap-1.5 px-2.5 py-1 text-[12px] border transition-colors',
        statusFilter === value
          ? 'border-border bg-muted text-foreground'
          : 'border-transparent text-muted-foreground/60 hover:text-muted-foreground',
      )}
    >
      {dotClass && <span className={cn('size-1.5 rounded-full shrink-0', dotClass)} />}
      {label}
      <span className={cn(
        'font-mono text-[10px]',
        statusFilter === value ? 'text-muted-foreground' : 'text-muted-foreground/40',
      )}>
        {count}
      </span>
    </button>
  )

  const renderEmpty = () => (
    <Empty className="m-4 border border-dashed border-border/60 bg-muted/10">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Bot />
        </EmptyMedia>
        <EmptyTitle>No agents yet</EmptyTitle>
        <EmptyDescription>
          Create an agent to run automations and workflows for this workspace.
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button variant="outline" size="xs" className="rounded-none">
          <Plus data-icon="inline-start" />
          Create agent
        </Button>
      </EmptyContent>
    </Empty>
  )

  const renderListView = () => (
    <div className="flex flex-col gap-1.5 p-4">
      {/* Header card */}
      <div className="flex items-center gap-3 border border-border/40 bg-muted/20 px-4 py-1.5">
        <div className="flex-1 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">AGENT</div>
        <div className="w-24 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">STATUS</div>
        <div className="w-32 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">ADAPTER</div>
        <div className="w-44 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">MODEL</div>
        <div className="w-28 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">CAPABILITIES</div>
        <div className="w-20 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">MODE</div>
        <div className="w-8 shrink-0" />
      </div>

      {filtered.length === 0 ? (
        <div className="py-8 text-center">
          <span className="font-mono text-[10px] text-muted-foreground/50">NO AGENTS MATCH</span>
        </div>
      ) : (
        filtered.map((agent) => (
          <AgentRow key={agent.id} agent={agent} to={`${base}/agents/${agent.slug}`} />
        ))
      )}
    </div>
  )

  const renderCardsView = () => (
    <ul className="grid grid-cols-1 gap-2 p-4 md:grid-cols-2 2xl:grid-cols-3">
      {filtered.map((agent) => (
        <li key={agent.id}>
          <AgentCard agent={agent} to={`${base}/agents/${agent.slug}`} />
        </li>
      ))}
    </ul>
  )

  const renderActiveRun = () => {
    if (!activeRun) return null
    //let activeRun = { run_id: '12345678-90ab-cdef-1234-567890abcdef', status: 'running' } // TODO: remove mock
    return (
      <div className="border-1 border-blue-500/30 bg-blue-500/5 p-2 flex items-center gap-3 m-4 mb-0">
        <Loader2 className="size-3 shrink-0 animate-spin text-blue-400" />
        <span className="font-mono text-[11px] text-blue-300">
          Run <span className="text-blue-200">{activeRun.run_id.slice(0, 8)}</span> in progress
        </span>
        <span className="ml-auto shrink-0 font-mono text-[10px] text-blue-400/60 uppercase tracking-widest">
          {activeRun.status}
        </span>
      </div>
    )
  }

  const renderMain = () => {
    if (isLoading) {
      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2">
          <Loader2 className="size-4 animate-spin text-muted-foreground" />
          <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">
            LOADING…
          </span>
        </div>
      )
    }

    if (agents.length === 0) return renderEmpty()

    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {view === 'list' ? renderListView() : renderCardsView()}
      </div>
    )
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      {/* Title bar */}
      <div className="flex items-center justify-between border-b border-dashed border-border/60 px-4 py-1 bg-muted/20">
        <div className="flex items-center gap-2.5">
          <h1 className="text-lg font-semibold tracking-tight">Agents</h1>
          {!isLoading && (
            <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">
              [{String(agents.length).padStart(2, '0')}]
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          {/* View toggle */}
          {!isLoading && agents.length > 0 && (
            <div className="flex items-center border border-border/60">
              <button
                onClick={() => setView('list')}
                className={cn(
                  'flex h-6 w-6 items-center justify-center transition-colors',
                  view === 'list' ? 'bg-muted text-foreground' : 'text-muted-foreground/50 hover:text-muted-foreground',
                )}
                aria-label="List view"
              >
                <LayoutList className="size-3" />
              </button>
              <button
                onClick={() => setView('cards')}
                className={cn(
                  'flex h-6 w-6 items-center justify-center transition-colors',
                  view === 'cards' ? 'bg-muted text-foreground' : 'text-muted-foreground/50 hover:text-muted-foreground',
                )}
                aria-label="Card view"
              >
                <LayoutGrid className="size-3" />
              </button>
            </div>
          )}

          <Button
            variant="outline"
            size="xs"
            className="rounded-none"
            disabled={isRunning || !workspaceId || agents.length === 0}
            onClick={() => triggerRun({ workspaceId: workspaceId!, body: {} })}
          >
            {isRunning
              ? <Loader2 className="size-3 animate-spin" />
              : <Play className="size-3" />}
            Run
          </Button>

          <Button variant="default" size="xs" className="rounded-none">
            <Plus className="size-3" />
            Create agent
          </Button>
        </div>
      </div>

      {/* Sub-header: search + status filters */}
      {!isLoading && agents.length > 0 && (
        <div className="flex items-center gap-2 border-b border-border/40 px-4 py-1.5">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3 text-muted-foreground/50" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search agents..."
              className="h-6 rounded-none border-border/60 pl-6 text-xs w-44 bg-background"
            />
          </div>

          <div className="h-3.5 w-px bg-border/60" />

          <div className="flex items-center">
            {renderStatusChip('all',      'All',      agents.length)}
            {renderStatusChip('online',   'Online',   onlineCount,   'bg-emerald-500')}
            {renderStatusChip('unstable', 'Unstable', unstableCount, 'bg-amber-500')}
            {renderStatusChip('offline',  'Offline',  offlineCount,  'bg-muted-foreground/40')}
          </div>
        </div>
      )}

      {renderActiveRun()}

      <div className="flex min-h-0 flex-1 flex-col">
        {renderMain()}
      </div>
    </div>
  )
}
