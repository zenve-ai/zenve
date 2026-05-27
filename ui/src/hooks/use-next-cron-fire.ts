import { CronExpressionParser } from 'cron-parser'
import { useEffect, useState } from 'react'

export function useNextCronFire(schedule: string | null): number | null {
  const [secondsUntil, setSecondsUntil] = useState<number | null>(null)

  useEffect(() => {
    if (!schedule) return

    const tick = () => {
      try {
        const interval = CronExpressionParser.parse(schedule)
        const next = interval.next().toDate()
        setSecondsUntil(Math.max(0, Math.round((next.getTime() - Date.now()) / 1000)))
      } catch {
        setSecondsUntil(null)
      }
    }

    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [schedule])

  return secondsUntil
}
