export function ProjectLoading() {
  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 p-8">
      <div className="size-8 animate-pulse rounded-none border border-border bg-muted/40" />
      <p className="text-sm">Loading projects…</p>
    </div>
  )
}
