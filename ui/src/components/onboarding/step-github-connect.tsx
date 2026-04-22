import { GitFork, GitBranch, Webhook, PencilLine, Check, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { useListGithubReposQuery } from '@/store/project'

interface StepGithubConnectProps {
  selectedRepo: string | null
  installUrl: string | null
  onRepoSelected: (repo: string | null) => void
  onConnectClick: () => void
}

const CHECKLIST = [
  { icon: GitBranch, label: 'Trigger agents on push and pull request events' },
  { icon: Webhook, label: 'Receive webhooks scoped to a single repository' },
  { icon: PencilLine, label: 'Read/write access — required to manage .zenve agent configs' },
]

export function StepGithubConnect({ selectedRepo, installUrl, onRepoSelected, onConnectClick }: StepGithubConnectProps) {
  // --- declarations ---
  const { data: repos, isLoading: reposLoading, error: reposError } = useListGithubReposQuery()

  const hasRepos = !reposLoading && !reposError && repos && repos.length > 0
  const connected = selectedRepo !== null

  // --- render helpers ---
  const renderToolbar = () => {
    if (reposLoading) {
      return (
        <div className="flex items-center gap-2 border-t border-dashed border-border/60 bg-muted/30 px-4 py-2">
          <Loader2 className="size-3.5 animate-spin text-muted-foreground/50" />
          <span className="text-[11px] font-mono text-muted-foreground/50">Loading repositories…</span>
        </div>
      )
    }

    if (hasRepos) {
      return (
        <div className="border-t border-dashed border-border/60 px-4 py-3 space-y-2">
          <p className="text-[10px] font-mono tracking-widest uppercase text-muted-foreground/50">
            Repository
          </p>
          <Select
            value={selectedRepo ?? ''}
            onValueChange={(val) => onRepoSelected(val || null)}
          >
            <SelectTrigger className="rounded-none font-mono text-sm h-8">
              <SelectValue placeholder="Select a repository…" />
            </SelectTrigger>
            <SelectContent className="rounded-none font-mono text-sm">
              {repos.map((repo) => (
                <SelectItem key={repo.id} value={repo.full_name} className="rounded-none font-mono text-sm">
                  {repo.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {!connected && (
            <p className="text-[10px] font-mono text-muted-foreground/40 uppercase tracking-widest">
              Optional — skip to continue
            </p>
          )}
        </div>
      )
    }

    return (
      <div className="flex items-center border-t border-dashed border-border/60 bg-muted/30 px-4 py-2">
        <Button
          size="xs"
          className={cn('rounded-none gap-1.5', connected && 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border border-emerald-500/40')}
          variant={connected ? 'ghost' : 'default'}
          disabled={!connected && installUrl === null}
          onClick={onConnectClick}
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
    )
  }

  // --- return ---
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
              {connected ? selectedRepo : 'Not connected'}
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

        {/* not-configured warning */}
        {!hasRepos && !reposLoading && installUrl === null && (
          <div className="mx-4 mb-3 border border-dashed border-amber-500/40 bg-amber-500/5 px-3 py-2 text-[11px] font-mono text-amber-400">
            VITE_GITHUB_APP_SLUG not configured — GitHub connect is unavailable.
          </div>
        )}

        {renderToolbar()}
      </div>
    </div>
  )
}
