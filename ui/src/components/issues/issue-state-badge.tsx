import { cn } from '@/lib/utils'

interface Props {
  state: 'open' | 'closed'
  className?: string
}

export function IssueStateBadge({ state, className }: Props) {
  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <span
        className={cn(
          'size-2 rounded-full',
          state === 'open' ? 'bg-emerald-500' : 'bg-muted-foreground/40',
        )}
      />
      <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground">
        {state === 'open' ? 'OPEN' : 'CLOSED'}
      </span>
    </span>
  )
}
