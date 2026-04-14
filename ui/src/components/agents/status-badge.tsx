import { cn } from '@/lib/utils'

const STATUS_CONFIG: Record<string, { label: string; className: string; dot: string }> = {
  active:   { label: 'LIVE', className: 'border-emerald-500/40 text-emerald-700 dark:text-emerald-400', dot: 'bg-emerald-500 animate-pulse' },
  paused:   { label: 'HOLD', className: 'border-amber-500/50 text-amber-600 dark:text-amber-400',     dot: 'bg-amber-500' },
  error:    { label: 'ERR',  className: 'border-red-500/40 text-red-600 dark:text-red-400',            dot: 'bg-red-500' },
  archived: { label: 'OFF',  className: 'border-border text-muted-foreground',                         dot: 'bg-muted-foreground/50' },
}

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status.toLowerCase()] ?? STATUS_CONFIG.active
  return (
    <span className={cn('flex items-center gap-1.5 border px-2 py-0.5 font-mono text-[10px] font-bold tracking-widest', cfg.className)}>
      <span className={cn('size-1.5 rounded-full', cfg.dot)} />
      {cfg.label}
    </span>
  )
}
