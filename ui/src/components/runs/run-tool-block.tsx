import type { ToolBlock } from '@/lib/run-events'

export function RunToolBlock({ block }: { block: ToolBlock }) {
  return (
    <div className="bg-slate-100 px-3 py-2 font-mono text-[11px]">

      {block.calls.map((call) => (
        <div key={call.key} className="flex flex-wrap items-baseline gap-x-2">
          <span className="text-sky-500">▶</span>
          <span className="font-bold text-slate-800">{call.line.tool}</span>
          {call.line.args.map(({ key, value }) => (
            <span key={key} className="text-slate-500">
              <span className="text-slate-400">{key}=</span>{value}
            </span>
          ))}
        </div>
      ))}
    </div>
  )
}
