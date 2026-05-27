import { useNextCronFire } from '@/hooks/use-next-cron-fire'

interface Props {
  schedule: string | null
}

export function ScheduleCountdown({ schedule }: Props) {
  const secondsUntil = useNextCronFire(schedule)

  if (secondsUntil === null) return null

  const h = Math.floor(secondsUntil / 3600)
  const m = Math.floor((secondsUntil % 3600) / 60)
  const s = secondsUntil % 60

  const label =
    h > 0
      ? `${h}h ${String(m).padStart(2, '0')}m`
      : m > 0
        ? `${m}m ${String(s).padStart(2, '0')}s`
        : `${s}s`

  return (
    <span className="font-mono text-[10px] tracking-widest text-muted-foreground uppercase">
      next {label}
    </span>
  )
}
