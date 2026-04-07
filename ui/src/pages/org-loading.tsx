import { Loader2 } from 'lucide-react'

export function OrgLoading() {
  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-3 bg-background text-muted-foreground">
      <Loader2 className="size-8 animate-spin" aria-hidden />
      <p className="text-sm">Loading organizations…</p>
    </div>
  )
}
