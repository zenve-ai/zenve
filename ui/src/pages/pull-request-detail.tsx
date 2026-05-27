import { Link, useParams } from 'react-router'
import { ChevronLeft, ExternalLink, Loader2, MessageSquare } from 'lucide-react'
import { PRCommentItem, PRStateBadge } from '@/components/pull-requests'
import { relativeTime } from '@/lib/utils'
import { useGetPullRequestQuery } from '@/store/pull-requests'

export default function PullRequestDetail() {
  const { workspaceId, prNumber } = useParams<{ workspaceId: string; prNumber: string }>()
  const base = workspaceId ? `/${workspaceId}` : ''
  const num = prNumber ? parseInt(prNumber, 10) : 0

  const skip = !workspaceId || !prNumber
  const { data: pr, isLoading, isError } = useGetPullRequestQuery(
    { workspaceId: workspaceId!, prNumber: num },
    { skip },
  )

  const renderLoading = () => (
    <div className="flex min-h-[50vh] items-center justify-center gap-2">
      <Loader2 className="size-4 animate-spin text-muted-foreground" />
      <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">LOADING…</span>
    </div>
  )

  const renderError = () => (
    <div className="flex min-h-[50vh] items-center justify-center">
      <span className="font-mono text-[11px] text-muted-foreground/60">Pull request not found</span>
    </div>
  )

  const renderSidebar = () => {
    if (!pr) return null
    return (
      <div className="flex flex-col gap-0">
        <div className="border-b border-border/60 bg-muted/10 px-4 py-1.5">
          <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">PROPERTIES</span>
        </div>

        <div className="flex flex-col gap-3 p-4">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">STATE</span>
            <PRStateBadge state={pr.state} draft={pr.draft} />
          </div>

          {pr.head && pr.base && (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">BRANCH</span>
              <span className="font-mono text-[11px] text-muted-foreground">
                {pr.head} → {pr.base}
              </span>
            </div>
          )}

          {pr.assignees.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">ASSIGNEES</span>
              <div className="flex flex-wrap gap-1">
                {pr.assignees.map((a) => (
                  <span
                    key={a}
                    className="flex size-6 items-center justify-center bg-muted font-mono text-[9px] font-bold text-muted-foreground"
                    title={a}
                  >
                    {a.trim().slice(0, 2).toUpperCase()}
                  </span>
                ))}
              </div>
            </div>
          )}

          {pr.labels.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">LABELS</span>
              <div className="flex flex-wrap gap-1">
                {pr.labels.map((label) => (
                  <span
                    key={label}
                    className="border border-dashed border-border px-1.5 font-mono text-[10px] text-muted-foreground"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {pr.url && (
            <a
              href={pr.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 font-mono text-[10px] text-muted-foreground/60 hover:text-muted-foreground"
            >
              <ExternalLink className="size-3" />
              View on GitHub
            </a>
          )}
        </div>

        <div className="border-t border-border/60 border-b border-border/60 bg-muted/10 px-4 py-1.5">
          <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">DETAILS</span>
        </div>

        <div className="flex flex-col gap-1.5 p-4">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] text-muted-foreground/50">Opened</span>
            <span className="font-mono text-[10px] text-muted-foreground">{relativeTime(pr.createdAt)} ago</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] text-muted-foreground/50">PR #</span>
            <span className="font-mono text-[10px] text-muted-foreground">#{String(pr.number).padStart(3, '0')}</span>
          </div>
        </div>
      </div>
    )
  }

  const renderDetail = () => {
    if (!pr) return null
    return (
      <div className="flex min-h-0 flex-1">
        {/* Left column */}
        <div className="flex min-w-0 flex-1 flex-col overflow-y-auto">
          <div className="border-b border-border/60 px-4 py-3">
            <h1 className="text-xl font-semibold leading-snug">{pr.title}</h1>
            <div className="mt-1.5 flex items-center gap-2">
              <PRStateBadge state={pr.state} draft={pr.draft} />
              <span className="font-mono text-[10px] text-muted-foreground/60">|</span>
              <span className="font-mono text-[11px] text-muted-foreground">
                #{String(pr.number).padStart(3, '0')}
              </span>
              <span className="font-mono text-[10px] text-muted-foreground/60">|</span>
              <span className="font-mono text-[10px] text-muted-foreground/60">
                opened {relativeTime(pr.createdAt)} ago
              </span>
            </div>
          </div>

          <div className="border-b border-border/60 p-4">
            {pr.body ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{pr.body}</p>
            ) : (
              <span className="font-mono text-[11px] text-muted-foreground/40">No description</span>
            )}
          </div>

          <div className="border-b border-border/60 bg-muted/10 px-4 py-1.5">
            <div className="flex items-center gap-1.5">
              <MessageSquare className="size-3 text-muted-foreground/60" />
              <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">
                {pr.comments.length === 0
                  ? 'COMMENTS'
                  : `${pr.comments.length} COMMENT${pr.comments.length !== 1 ? 'S' : ''}`}
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-3 p-4">
            {pr.comments.length === 0 ? (
              <span className="font-mono text-[11px] text-muted-foreground/40">No comments yet</span>
            ) : (
              pr.comments.map((c, i) => <PRCommentItem key={i} comment={c} />)
            )}
          </div>
        </div>

        {/* Right column — meta panel */}
        <div className="w-64 xl:w-80 2xl:w-96 shrink-0 border-l border-border/60">
          {renderSidebar()}
        </div>
      </div>
    )
  }

  const renderMain = () => {
    if (isLoading) return renderLoading()
    if (isError) return renderError()
    return renderDetail()
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex items-center gap-2 border-b border-border/60 bg-muted/20 px-4 py-1.5">
        <Link
          to={`${base}/pull-requests`}
          className="flex items-center gap-1 font-mono text-[10px] text-muted-foreground/60 hover:text-muted-foreground"
        >
          <ChevronLeft className="size-3" />
          PULL REQUESTS
        </Link>
      </div>
      {renderMain()}
    </div>
  )
}
