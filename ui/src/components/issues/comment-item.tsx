import { User } from 'lucide-react'
import { relativeTime } from '@/lib/utils'
import type { IssueComment } from '@/types'

interface Props {
  comment: IssueComment
}

function initials(name: string) {
  return name.trim().slice(0, 2).toUpperCase()
}

export function CommentItem({ comment }: Props) {
  const author = comment.author?.trim() || ''
  const abbr = initials(author)

  return (
    <div className="border border-border/60">
      <div className="flex items-center gap-2 border-b border-border/60 bg-muted/20 px-3 py-1.5">
        <span className="flex size-6 shrink-0 items-center justify-center bg-muted font-mono text-[9px] font-bold text-muted-foreground">
          {abbr ? abbr : <User className="size-3 text-muted-foreground/60" />}
        </span>
        <span className="text-[13px] font-medium">{author || 'unknown'}</span>
        <span className="font-mono text-[10px] text-muted-foreground/60">|</span>
        <span className="font-mono text-[10px] text-muted-foreground/60">
          {relativeTime(comment.createdAt)} ago
        </span>
      </div>
      <div className="px-4 py-3 text-sm whitespace-pre-wrap">{comment.body}</div>
    </div>
  )
}
