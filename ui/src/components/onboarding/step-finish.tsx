import { Check, FolderOpen, GitFork, Bot } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface StepFinishProps {
  projectName: string
  projectDescription: string
  githubRepo: string | null
  selectedAgentCount: number
  onGetStarted: () => void
  isLoading: boolean
  error: string | null
}

export function StepFinish({
  projectName,
  projectDescription,
  githubRepo,
  selectedAgentCount,
  onGetStarted,
  isLoading,
  error,
}: StepFinishProps) {
  // --- render helpers ---
  const renderSummaryRow = (
    icon: React.ReactNode,
    label: string,
    value: string,
    highlight?: boolean,
  ) => (
    <div className="flex items-start gap-3 border-b border-dashed border-border/60 px-4 py-3 last:border-b-0">
      <div className="mt-0.5 text-muted-foreground/50">{icon}</div>
      <div className="flex-1">
        <p className="text-[10px] font-mono tracking-widest uppercase text-muted-foreground/50">{label}</p>
        <p className={`text-sm font-mono font-medium leading-tight mt-0.5 ${highlight ? 'text-emerald-500' : ''}`}>
          {value}
        </p>
      </div>
      {highlight && <Check className="mt-0.5 size-4 text-emerald-500 shrink-0" />}
    </div>
  )

  // --- return ---
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/50">
          Step 04 / 04
        </p>
        <h2 className="mt-1 text-lg font-semibold leading-tight">Ready to launch</h2>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Review your setup and start using Zenve.
        </p>
      </div>

      <div className="border border-dashed border-border/60">
        {renderSummaryRow(
          <FolderOpen className="size-4" />,
          'Project name',
          projectName,
        )}
        {projectDescription && renderSummaryRow(
          <FolderOpen className="size-4" />,
          'Description',
          projectDescription,
        )}
        {renderSummaryRow(
          <GitFork className="size-4" />,
          'GitHub',
          githubRepo ?? 'Not connected',
          githubRepo !== null,
        )}
        {renderSummaryRow(
          <Bot className="size-4" />,
          'Agents',
          selectedAgentCount > 0
            ? `${selectedAgentCount} agent${selectedAgentCount !== 1 ? 's' : ''} selected`
            : 'None selected',
          selectedAgentCount > 0,
        )}
      </div>

      {error && (
        <div className="border border-dashed border-red-500/40 bg-red-500/5 px-3 py-2 text-[11px] font-mono text-red-400">
          {error}
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          size="xs"
          className="rounded-none gap-1.5"
          disabled={isLoading}
          onClick={onGetStarted}
        >
          <Check className="size-3.5" />
          {isLoading ? 'Creating…' : 'Get Started'}
        </Button>
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground/40">
          You can always change settings later
        </span>
      </div>
    </div>
  )
}
