export function PlaceholderTab({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="p-4">
      <p className="text-[13px] font-medium">{title}</p>
      <div className="mt-3 text-[12px] text-muted-foreground">{children}</div>
    </div>
  )
}
