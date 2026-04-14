export function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="mt-2 max-h-[min(50vh,420px)] overflow-auto border border-border bg-muted/20 p-3 font-mono text-[11px] leading-relaxed">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}
