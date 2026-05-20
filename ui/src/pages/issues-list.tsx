import { useState } from 'react'
import { useParams } from 'react-router'
import { CircleDot, Loader2, Plus } from 'lucide-react'
import { toast } from 'sonner'
import { CreateIssueDialog, IssueRow } from '@/components/issues'
import { Button } from '@/components/ui/button'
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty'
import { cn } from '@/lib/utils'
import { useListIssuesQuery, useCreateIssueMutation } from '@/store/issues'

type StateFilter = 'open' | 'closed' | 'all'

const FILTERS: { value: StateFilter; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'closed', label: 'Closed' },
  { value: 'all', label: 'All' },
]

export default function IssuesList() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const base = workspaceId ? `/${workspaceId}` : ''
  const [stateFilter, setStateFilter] = useState<StateFilter>('open')
  const [createOpen, setCreateOpen] = useState(false)

  const { data: issues = [], isLoading } = useListIssuesQuery(
    { workspaceId: workspaceId!, state: stateFilter === 'all' ? undefined : stateFilter },
    { skip: !workspaceId },
  )
  const [createIssue, { isLoading: isCreating }] = useCreateIssueMutation()

  const handleCreate = async (title: string, body: string) => {
    if (!workspaceId) return
    try {
      await createIssue({ workspaceId, body: { title, body: body || undefined } }).unwrap()
      toast.success('Issue created')
      setCreateOpen(false)
    } catch {
      toast.error('Could not create issue')
    }
  }

  const renderFilterTabs = () => (
    <div className="flex items-center">
      {FILTERS.map((f) => (
        <button
          key={f.value}
          onClick={() => setStateFilter(f.value)}
          className={cn(
            'border-b-2 px-3 py-2 font-mono text-[11px] font-bold tracking-widest transition-colors',
            stateFilter === f.value
              ? 'border-foreground text-foreground'
              : 'border-transparent text-muted-foreground/60 hover:text-muted-foreground',
          )}
        >
          {f.label.toUpperCase()}
        </button>
      ))}
    </div>
  )

  const renderLoading = () => (
    <div className="flex flex-1 flex-col items-center justify-center gap-2">
      <Loader2 className="size-4 animate-spin text-muted-foreground" />
      <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">LOADING...</span>
    </div>
  )

  const renderEmpty = () => (
    <Empty className="m-4 border border-dashed border-border/60 bg-muted/10">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <CircleDot />
        </EmptyMedia>
        <EmptyTitle>No issues</EmptyTitle>
        <EmptyDescription>
          {stateFilter === 'closed'
            ? 'No closed issues for this workspace.'
            : 'No open issues found for this workspace.'}
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button variant="outline" size="xs" className="rounded-none" onClick={() => setCreateOpen(true)}>
          <Plus data-icon="inline-start" />
          New issue
        </Button>
      </EmptyContent>
    </Empty>
  )

  const renderList = () => (
    <div className="flex flex-col gap-1.5 p-4">
      {issues.map((issue) => (
        <IssueRow key={issue.id} issue={issue} to={`${base}/issues/${issue.id}`} />
      ))}
    </div>
  )

  const renderContent = () => {
    if (isLoading) return renderLoading()
    if (issues.length === 0) return renderEmpty()
    return renderList()
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-border/60 bg-muted/20 px-4 py-1">
        <div className="flex items-center gap-2.5">
          <h1 className="text-lg font-semibold tracking-tight">Issues</h1>
          {!isLoading && (
            <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">
              [{String(issues.length).padStart(2, '0')}]
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          {renderFilterTabs()}
          <Button variant="default" size="xs" className="rounded-none" onClick={() => setCreateOpen(true)}>
            <Plus className="size-3" />
            New issue
          </Button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        {renderContent()}
      </div>

      <CreateIssueDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={handleCreate}
        isSubmitting={isCreating}
      />
    </div>
  )
}
