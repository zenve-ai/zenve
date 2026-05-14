import type { OutputBlock } from '@/lib/run-events'

export function RunOutputBlock({ block }: { block: OutputBlock }) {
  return (
    <div className="bg-white px-3 py-2 font-mono text-[11px]">

      {block.lines.map((line, i) => (
        <div key={i} className="whitespace-pre-wrap break-all text-slate-800">
          {line}
        </div>
      ))}
    </div>
  )
}
