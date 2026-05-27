import { useState } from 'react'
import { useParams } from 'react-router'
import { GitPullRequest, Loader2 } from 'lucide-react'
import { PRRow } from '@/components/pull-requests'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { cn } from '@/lib/utils'
import { useListPullRequestsQuery } from '@/store/pull-requests'

type StateFilter = 'open' | 'closed' | 'all'

const FILTERS: { value: StateFilter; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'closed', label: 'Closed' },
  { value: 'all', label: 'All' },
]

export default function PullRequestsList() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const base = workspaceId ? `/${workspaceId}` : ''
  const [stateFilter, setStateFilter] = useState<StateFilter>('open')

  const { data: prs = [], isLoading, isFetching } = useListPullRequestsQuery(
    {
      workspaceId: workspaceId!,
      state: stateFilter === 'all' ? 'all' : stateFilter,
      limit: stateFilter !== 'open' ? 50 : undefined,
    },
    { skip: !workspaceId },
  )

  const renderFilterChips = () => (
    <div className="flex items-center gap-2 border-b border-border/40 px-4 py-1.5">
      {FILTERS.map((f) => (
        <button
          key={f.value}
          onClick={() => setStateFilter(f.value)}
          className={cn(
            'flex items-center gap-1.5 px-2.5 py-1 text-[12px] border transition-colors',
            stateFilter === f.value
              ? 'border-border bg-muted text-foreground'
              : 'border-transparent text-muted-foreground/60 hover:text-muted-foreground',
          )}
        >
          {f.value === 'open' && <span className="size-1.5 rounded-full bg-emerald-500 shrink-0" />}
          {f.value === 'closed' && <span className="size-1.5 rounded-full bg-muted-foreground/40 shrink-0" />}
          {f.label}
          {stateFilter === f.value && !isLoading && !isFetching && (
            <span className="font-mono text-[10px] text-muted-foreground">
              {prs.length}
            </span>
          )}
        </button>
      ))}
    </div>
  )

  const renderLoading = () => (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2">
      <Loader2 className="size-4 animate-spin text-muted-foreground" />
      <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">LOADING…</span>
    </div>
  )

  const renderEmpty = () => (
    <Empty className="m-4 border border-dashed border-border/60 bg-muted/10">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <GitPullRequest />
        </EmptyMedia>
        <EmptyTitle>No pull requests</EmptyTitle>
        <EmptyDescription>
          {stateFilter === 'closed'
            ? 'No closed pull requests found.'
            : stateFilter === 'all'
              ? 'No pull requests found.'
              : 'No open pull requests found for this workspace.'}
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent />
    </Empty>
  )

  const renderList = () => (
    <div className="flex flex-col gap-1.5 p-4">
      <div className="flex items-center gap-3 border border-border/40 bg-muted/20 px-4 py-1.5">
        <div className="w-16 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">STATE</div>
        <div className="w-10 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">#</div>
        <div className="flex-1 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">TITLE</div>
        <div className="hidden shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50 sm:block">BRANCH</div>
        <div className="w-10 shrink-0 text-right font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">OPENED</div>
      </div>

      {prs.map((pr) => (
        <PRRow key={pr.number} pr={pr} to={`${base}/pull-requests/${pr.number}`} />
      ))}
    </div>
  )

  const renderContent = () => {
    if (isLoading || isFetching) return renderLoading()
    if (prs.length === 0) return renderEmpty()
    return renderList()
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-dashed border-border/60 bg-muted/20 px-4 py-1">
        <div className="flex items-center gap-2.5">
          <h1 className="text-lg font-semibold tracking-tight">Pull Requests</h1>
          {!isLoading && !isFetching && (
            <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">
              [{String(prs.length).padStart(2, '0')}]
            </span>
          )}
        </div>
      </div>

      {renderFilterChips()}

      <div className="flex min-h-0 flex-1 flex-col">
        {renderContent()}
      </div>
    </div>
  )
}
