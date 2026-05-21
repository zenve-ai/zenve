import { User } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { relativeTime } from '@/lib/utils'
import type { IssueComment } from '@/types'

interface Props {
  comment: IssueComment
}

function initials(name: string) {
  return name.trim().slice(0, 2).toUpperCase()
}

function commentTone(body: string): 'error' | null {
  if (/run failed/i.test(body)) return 'error'
  return null
}

const toneStyles = {
  error: { border: 'border-red-500/30', header: 'bg-red-500/5' },
}

export function CommentItem({ comment }: Props) {
  const author = comment.author?.trim() || ''
  const abbr = initials(author)
  const tone = commentTone(comment.body)
  const styles = tone ? toneStyles[tone] : { border: 'border-border/60', header: 'bg-muted/20' }

  return (
    <div className={`border ${styles.border}`}>
      <div className={`flex items-center gap-2 border-b ${styles.border} ${styles.header} px-3 py-1.5`}>
        <span className="flex size-6 shrink-0 items-center justify-center bg-muted font-mono text-[9px] font-bold text-muted-foreground">
          {abbr ? abbr : <User className="size-3 text-muted-foreground/60" />}
        </span>
        <span className="text-[13px] font-medium">{author || 'unknown'}</span>
        <span className="font-mono text-[10px] text-muted-foreground/60">|</span>
        <span className="font-mono text-[10px] text-muted-foreground/60">
          {relativeTime(comment.createdAt)} ago
        </span>
      </div>
      <div className="px-4 py-3 text-sm prose prose-sm max-w-none
        prose-p:my-1 prose-pre:rounded-none prose-pre:bg-muted/40 prose-pre:border prose-pre:border-border/60
        prose-code:text-[11px] prose-code:bg-muted/40 prose-code:px-1 prose-code:rounded-none prose-code:font-mono
        prose-headings:font-mono prose-headings:tracking-tight prose-a:text-primary
        prose-p:text-foreground prose-li:text-foreground prose-headings:text-foreground prose-strong:text-foreground">
        <ReactMarkdown>{comment.body}</ReactMarkdown>
      </div>
    </div>
  )
}
