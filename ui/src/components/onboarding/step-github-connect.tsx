import { GitFork, GitBranch, Webhook, Lock, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface StepGithubConnectProps {
  githubStatus: 'idle' | 'connected'
  onToggle: () => void
}

const CHECKLIST = [
  { icon: GitBranch, label: 'Trigger agents on push and pull request events' },
  { icon: Webhook, label: 'Receive webhooks scoped to a single repository' },
  { icon: Lock, label: 'Read-only access — no write permissions required' },
]

export function StepGithubConnect({ githubStatus, onToggle }: StepGithubConnectProps) {
  const connected = githubStatus === 'connected'

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/50">
          Step 02 / 04
        </p>
        <h2 className="mt-1 text-lg font-semibold leading-tight">Connect GitHub</h2>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Link a repository so Zenve agents can respond to code events.
        </p>
      </div>

      <div className="border border-dashed border-border/60">
        {/* header */}
        <div className="flex items-center gap-3 border-b border-dashed border-border/60 px-4 py-3">
          <div className={cn('w-[3px] self-stretch', connected ? 'bg-emerald-500' : 'bg-muted-foreground/30')} />
          <GitFork className="size-4 text-muted-foreground/60" />
          <div>
            <p className="text-[10px] font-mono tracking-widest uppercase text-muted-foreground/50">
              GitHub App
            </p>
            <p className={cn('text-sm font-mono font-medium leading-tight', connected && 'text-emerald-500')}>
              {connected ? 'Connected' : 'Not connected'}
            </p>
          </div>
          {connected && <Check className="ml-auto size-4 text-emerald-500" />}
        </div>

        {/* checklist */}
        <div className="px-4 py-4">
          <p className="mb-2 text-[10px] font-mono tracking-widest uppercase text-muted-foreground/50">
            What this enables
          </p>
          <ul className="space-y-2 text-sm font-mono text-muted-foreground">
            {CHECKLIST.map(({ icon: Icon, label }) => (
              <li key={label} className="flex items-center gap-2">
                <Icon className="size-3.5 shrink-0 text-muted-foreground/60" />
                <span>{label}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* toolbar */}
        <div className="flex items-center border-t border-dashed border-border/60 bg-muted/30 px-4 py-2">
          <Button
            size="xs"
            className={cn('rounded-none gap-1.5', connected && 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border border-emerald-500/40')}
            variant={connected ? 'ghost' : 'default'}
            onClick={onToggle}
          >
            {connected ? (
              <>
                <Check className="size-3.5" />
                GitHub Connected
              </>
            ) : (
              <>
                <GitFork className="size-3.5" />
                Connect GitHub
              </>
            )}
          </Button>
          {!connected && (
            <span className="ml-3 text-[10px] font-mono text-muted-foreground/40 uppercase tracking-widest">
              Optional — skip to continue
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
