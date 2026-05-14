import { cn } from '@/lib/utils'
import type { StatusLine } from '@/lib/run-events'

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

export function RunStatusLine({ line }: { line: StatusLine }) {
  const { subtype, data } = line

  const renderContent = () => {
    switch (subtype) {
      case 'agent.completed': {
        const dur = typeof data.duration_seconds === 'number' ? formatDuration(data.duration_seconds) : ''
        return (
          <span className="font-bold text-emerald-600">
            ✓ completed{dur ? <span className="ml-2 font-normal text-emerald-500">{dur}</span> : null}
          </span>
        )
      }
      case 'agent.failed': {
        const err = (data.error as string | undefined) ?? 'failed'
        return <span className="text-red-500">✗ failed  {err.slice(0, 120)}</span>
      }
      case 'agent.nothing_to_do':
        return <span className="text-slate-400">— nothing to do</span>

      case 'agent.started':
        return <span className="text-slate-500">● started</span>

      case 'agent.claimed_issue':
      case 'agent.claimed_pr': {
        const num = data.number as number
        const title = (data.title as string | undefined) ?? ''
        return (
          <span className="text-sky-600">
            #{num}  {title}
          </span>
        )
      }

      case 'adapter.usage': {
        const inp = (data.input_tokens as number | undefined) ?? 0
        const out = (data.output_tokens as number | undefined) ?? 0
        const cost = data.cost_usd as number | undefined
        const cache = data.cache_read_input_tokens as number | undefined
        return (
          <span className="text-slate-500">
            <span className="mr-2 font-bold text-amber-500">usage</span>
            ↑ {inp.toLocaleString()} · ↓ {out.toLocaleString()}
            {cache ? ` · cache ${cache.toLocaleString()}` : ''}
            {cost != null ? ` · $${cost.toFixed(4)}` : ''}
          </span>
        )
      }

      case 'adapter.error': {
        const msg = (data.message as string | undefined) ?? 'error'
        return <span className="text-red-500">✗ error  {msg.slice(0, 120)}</span>
      }

      case 'run.started': {
        const repo = (data.repo as string | undefined) ?? ''
        return <span className="text-slate-500">run  {repo}</span>
      }

      case 'run.completed':
        return <span className="font-bold text-emerald-600">✓ committed agent run</span>

      case 'run.failed': {
        const err = (data.error as string | undefined) ?? 'failed'
        return <span className="text-red-500">✗ run failed  {err.slice(0, 120)}</span>
      }

      case 'run.committing':
        return <span className="text-slate-400">⟳ committing</span>

      case 'snapshot.fetched': {
        const issues = (data.issues as number | undefined) ?? 0
        const prs = (data.pull_requests as number | undefined) ?? 0
        return (
          <span className="text-slate-400">
            snapshot  {issues} issues · {prs} PRs
          </span>
        )
      }

      case 'pipeline.transition': {
        const from = (data.from as string | undefined) ?? ''
        const toRaw = data.to
        const to = Array.isArray(toRaw) ? toRaw.join(', ') : (toRaw as string | undefined) ?? ''
        return (
          <span className="text-slate-500">
            <span className="text-slate-400">↳</span>
            <span className="mx-1 text-sky-600">{from}</span>
            <span className="text-slate-400">→</span>
            <span className="ml-1 text-sky-600">{to}</span>
          </span>
        )
      }

      case 'pipeline.end': {
        const from = (data.from as string | undefined) ?? ''
        return (
          <span className="text-slate-500">
            <span className="text-slate-400">↳</span>
            <span className="mx-1 text-sky-600">{from}</span>
            <span className="text-slate-400">→ done</span>
          </span>
        )
      }

      default:
        return <span className="text-slate-300">{subtype}</span>
    }
  }

  const isError = subtype === 'agent.failed' || subtype === 'run.failed' || subtype === 'adapter.error'

  return (
    <div
      className={cn(
        'px-3 py-1.5 font-mono text-[11px]',
        isError ? 'bg-red-50' : 'bg-slate-50',
      )}
    >
      {line.agent && (
        <span className="mr-2 text-slate-300">{line.agent}</span>
      )}
      {renderContent()}
    </div>
  )
}
