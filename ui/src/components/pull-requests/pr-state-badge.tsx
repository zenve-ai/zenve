import { cn } from '@/lib/utils'

interface Props {
  state: 'open' | 'closed'
  draft?: boolean
  className?: string
}

export function PRStateBadge({ state, draft = false, className }: Props) {
  const isDraft = draft && state === 'open'
  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <span
        className={cn(
          'size-2 rounded-full',
          isDraft
            ? 'bg-amber-400'
            : state === 'open'
              ? 'bg-emerald-500'
              : 'bg-muted-foreground/40',
        )}
      />
      <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground">
        {isDraft ? 'DRAFT' : state === 'open' ? 'OPEN' : 'CLOSED'}
      </span>
    </span>
  )
}
