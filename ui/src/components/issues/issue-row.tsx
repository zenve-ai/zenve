import { Link } from 'react-router'
import { cn, relativeTime } from '@/lib/utils'
import type { Issue } from '@/types'

interface Props {
  issue: Issue
  to: string
}

function initials(name: string) {
  return name.trim().slice(0, 2).toUpperCase() || '?'
}

export function IssueRow({ issue, to }: Props) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 border border-border/60 px-4 py-2.5 transition-colors hover:bg-muted/20"
    >
      <span
        className={cn(
          'size-2 shrink-0 rounded-full',
          issue.state === 'open' ? 'bg-emerald-500' : 'bg-muted-foreground/40',
        )}
      />

      <span className="w-10 shrink-0 font-mono text-[11px] text-muted-foreground">
        #{String(issue.id).padStart(3, '0')}
      </span>

      <span className="flex min-w-0 flex-1 items-center gap-2">
        <span className="truncate text-sm font-medium">{issue.title}</span>
        {issue.labels.length > 0 && (
          <span className="flex shrink-0 items-center gap-1">
            {issue.labels.slice(0, 3).map((label) => (
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

      {issue.assignees.length > 0 && (
        <span className="flex shrink-0 items-center gap-1">
          {issue.assignees.slice(0, 2).map((a) => (
            <span
              key={a}
              className="flex size-5 items-center justify-center bg-muted font-mono text-[9px] font-bold text-muted-foreground"
              title={a}
            >
              {initials(a)}
            </span>
          ))}
        </span>
      )}

      <span className="w-10 shrink-0 text-right font-mono text-[10px] text-muted-foreground/60">
        {relativeTime(issue.updatedAt)}
      </span>
    </Link>
  )
}
