import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { ChevronLeft, Loader2, MessageSquare } from 'lucide-react'
import { toast } from 'sonner'
import { CommentItem, IssueMetaPanel, IssueStateBadge } from '@/components/issues'
import { Button } from '@/components/ui/button'
import { relativeTime } from '@/lib/utils'
import {
  useGetIssueQuery,
  useListCommentsQuery,
  useUpdateIssueMutation,
  useAddCommentMutation,
} from '@/store/issues'

export default function IssueDetail() {
  const { workspaceId, issueId } = useParams<{ workspaceId: string; issueId: string }>()
  const base = workspaceId ? `/${workspaceId}` : ''
  const id = issueId ? parseInt(issueId, 10) : 0
  const [commentBody, setCommentBody] = useState('')

  const skip = !workspaceId || !issueId
  const { data: issue, isLoading, isError } = useGetIssueQuery(
    { workspaceId: workspaceId!, issueId: id },
    { skip },
  )
  const { data: comments = [], isLoading: commentsLoading } = useListCommentsQuery(
    { workspaceId: workspaceId!, issueId: id },
    { skip },
  )
  const [updateIssue, { isLoading: isUpdating }] = useUpdateIssueMutation()
  const [addComment, { isLoading: isAddingComment }] = useAddCommentMutation()

  const handleToggleState = async () => {
    if (!workspaceId || !issue) return
    try {
      await updateIssue({
        workspaceId,
        issueId: id,
        body: { state: issue.state === 'open' ? 'closed' : 'open' },
      }).unwrap()
      toast.success(issue.state === 'open' ? 'Issue closed' : 'Issue reopened')
    } catch {
      toast.error('Could not update issue')
    }
  }

  const handleUpdateLabels = async (labels: string[]) => {
    if (!workspaceId) return
    try {
      await updateIssue({ workspaceId, issueId: id, body: { labels } }).unwrap()
    } catch {
      toast.error('Could not update labels')
    }
  }

  const handleAddComment = async () => {
    if (!workspaceId || !commentBody.trim()) return
    try {
      await addComment({ workspaceId, issueId: id, body: commentBody.trim() }).unwrap()
      setCommentBody('')
      toast.success('Comment added')
    } catch {
      toast.error('Could not add comment')
    }
  }

  const renderLoading = () => (
    <div className="flex min-h-[50vh] items-center justify-center gap-2">
      <Loader2 className="size-4 animate-spin text-muted-foreground" />
      <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">LOADING…</span>
    </div>
  )

  const renderError = () => (
    <div className="flex min-h-[50vh] items-center justify-center">
      <span className="font-mono text-[11px] text-muted-foreground/60">Issue not found</span>
    </div>
  )

  const renderComments = () => (
    <div className="flex flex-col gap-3 p-4">
      {commentsLoading ? (
        <div className="flex items-center gap-2">
          <Loader2 className="size-3 animate-spin text-muted-foreground" />
          <span className="font-mono text-[10px] text-muted-foreground/60">LOADING…</span>
        </div>
      ) : (
        comments.map((c) => <CommentItem key={c.id} comment={c} />)
      )}

      <div className="mt-2 flex flex-col gap-2">
        <textarea
          value={commentBody}
          onChange={(e) => setCommentBody(e.target.value)}
          placeholder="Leave a comment…"
          rows={3}
          className="w-full resize-none border border-border/60 bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground/40 focus:border-border focus:outline-none"
        />
        <div className="flex justify-end">
          <Button
            variant="default"
            size="xs"
            className="rounded-none"
            onClick={handleAddComment}
            disabled={isAddingComment || !commentBody.trim()}
          >
            {isAddingComment ? <Loader2 className="size-3 animate-spin" /> : 'Comment'}
          </Button>
        </div>
      </div>
    </div>
  )

  const renderDetail = () => {
    if (!issue) return null
    return (
      <div className="flex min-h-0 flex-1">
        {/* Left column */}
        <div className="flex min-w-0 flex-1 flex-col overflow-y-auto">
          {/* Issue header */}
          <div className="border-b border-border/60 px-4 py-3">
            <h1 className="text-xl font-semibold leading-snug">{issue.title}</h1>
            <div className="mt-1.5 flex items-center gap-2">
              <IssueStateBadge state={issue.state} />
              <span className="font-mono text-[10px] text-muted-foreground/60">|</span>
              <span className="font-mono text-[11px] text-muted-foreground">
                #{String(issue.id).padStart(3, '0')}
              </span>
              <span className="font-mono text-[10px] text-muted-foreground/60">|</span>
              <span className="font-mono text-[10px] text-muted-foreground/60">
                opened {relativeTime(issue.createdAt)} ago
              </span>
            </div>
          </div>

          {/* Body */}
          <div className="border-b border-border/60 p-4">
            {issue.body ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{issue.body}</p>
            ) : (
              <span className="font-mono text-[11px] text-muted-foreground/40">No description</span>
            )}
          </div>

          {/* Comments header */}
          <div className="border-b border-border/60 bg-muted/10 px-4 py-1.5">
            <div className="flex items-center gap-1.5">
              <MessageSquare className="size-3 text-muted-foreground/60" />
              <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">
                {comments.length === 0 ? 'COMMENTS' : `${comments.length} COMMENT${comments.length !== 1 ? 'S' : ''}`}
              </span>
            </div>
          </div>

          {renderComments()}
        </div>

        {/* Right column — meta panel */}
        <div className="w-64 xl:w-80 2xl:w-96 shrink-0 border-l border-border/60">
          <IssueMetaPanel workspaceId={workspaceId!} issue={issue} onToggleState={handleToggleState} onUpdateLabels={handleUpdateLabels} isUpdating={isUpdating} />
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
          to={`${base}/issues`}
          className="flex items-center gap-1 font-mono text-[10px] text-muted-foreground/60 hover:text-muted-foreground"
        >
          <ChevronLeft className="size-3" />
          ISSUES
        </Link>
      </div>
      {renderMain()}
    </div>
  )
}
