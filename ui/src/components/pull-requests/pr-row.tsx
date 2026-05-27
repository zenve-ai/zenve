import { Link } from 'react-router'
import { cn, relativeTime } from '@/lib/utils'
import type { PullRequest } from '@/types'
import { PRStateBadge } from './pr-state-badge'

interface Props {
  pr: PullRequest
  to: string
}

export function PRRow({ pr, to }: Props) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 border border-border/60 px-4 py-2.5 transition-colors hover:bg-muted/20"
    >
      <PRStateBadge state={pr.state} draft={pr.draft} />

      <span className="w-10 shrink-0 font-mono text-[11px] text-muted-foreground">
        #{String(pr.number).padStart(3, '0')}
      </span>

      <span className="flex min-w-0 flex-1 items-center gap-2">
        <span className="truncate text-sm font-medium">{pr.title}</span>
        {pr.labels.length > 0 && (
          <span className="flex shrink-0 items-center gap-1">
            {pr.labels.slice(0, 3).map((label) => (
              <span
                key={label}
                className="border border-dashed border-border px-1.5 font-mono text-[10px] text-muted-foreground"
              >
                {label}
              </span>
            ))}
          </span>
        )}
      </span>

      {pr.head && pr.base && (
        <span className={cn(
          'hidden shrink-0 items-center gap-1 font-mono text-[10px] text-muted-foreground/60 sm:flex',
        )}>
          <span>{pr.head}</span>
          <span>→</span>
          <span>{pr.base}</span>
        </span>
      )}

      <span className="w-10 shrink-0 text-right font-mono text-[10px] text-muted-foreground/60">
        {relativeTime(pr.createdAt)}
      </span>
    </Link>
  )
}
