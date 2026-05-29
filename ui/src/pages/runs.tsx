import { useParams } from 'react-router'
import { Activity, Loader2 } from 'lucide-react'
import { ActiveRunPanel, RunRow } from '@/components/runs'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { useListGroupedRunsQuery } from '@/store/runs'

export default function RunsPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()

  const { data: runs = [], isLoading } = useListGroupedRunsQuery(
    { workspaceId: workspaceId! },
    { skip: !workspaceId, pollingInterval: 4000 },
  )

  const activeRun = runs.find((r) => r.status === 'running' || r.status === 'queued') ?? null
  const pastRuns = runs.filter((r) => r !== activeRun)

  const renderEmpty = () => (
    <Empty className="m-4 border border-dashed border-border/60 bg-muted/10">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Activity />
        </EmptyMedia>
        <EmptyTitle>No runs yet</EmptyTitle>
        <EmptyDescription>
          Trigger a run from the Agents page to see execution history here.
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent />
    </Empty>
  )

  const renderHeader = () => (
    <div className="flex items-center gap-0 border-b border-border/40 bg-muted/20">
      <div className="w-[3px] self-stretch" />
      <div className="flex flex-1 items-center gap-4 px-4 py-1.5">
        <span className="w-20 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/40">
          RUN ID
        </span>
        <span className="w-20 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/40">
          STATUS
        </span>
        <span className="w-16 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/40">
          WHEN
        </span>
        <span className="w-16 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/40">
          DURATION
        </span>
        <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/40">
          AGENTS
        </span>
      </div>
    </div>
  )

  const renderContent = () => (
    <div className="flex flex-col gap-1.5 p-4">
      {renderHeader()}
      <div className="flex flex-col gap-1">
        {pastRuns.map((run) => (
          <RunRow key={run.run_id} run={run} />
        ))}
      </div>
    </div>
  )

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

    if (runs.length === 0) return renderEmpty()

    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {activeRun && <ActiveRunPanel run={activeRun} />}
        {pastRuns.length > 0 && renderContent()}
      </div>
    )
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      {/* Title bar */}
      <div className="flex items-center justify-between border-b border-dashed border-border/60 px-4 py-1 bg-muted/20">
        <div className="flex items-center gap-2.5">
          <h1 className="text-lg font-semibold tracking-tight">Runs</h1>
          {!isLoading && (
            <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">
              [{String(runs.length).padStart(2, '0')}]
            </span>
          )}
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        {renderMain()}
      </div>
    </div>
  )
}
