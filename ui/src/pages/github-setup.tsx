import { useParams } from 'react-router'
import { GitFork, GitBranch, Webhook, Lock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAppSelector } from '@/store/hooks'
import { selectCurrentProject } from '@/store/project'
import config from '@/config'

const PROJECT_SESSION_KEY = 'zenve_project_session'

export default function GitHubSetup() {
  // --- declarations ---
  const { projectSlug } = useParams<{ projectSlug: string }>()
  const project = useAppSelector(selectCurrentProject)
  const callbackUrl = `${window.location.origin}/github/callback`
  const installUrl = config.githubAppSlug
    ? `https://github.com/apps/${config.githubAppSlug}/installations/new?redirect_url=${encodeURIComponent(callbackUrl)}`
    : null

  // --- render helpers ---
  const renderChecklist = () => (
    <ul className="space-y-2 text-sm font-mono text-muted-foreground">
      {[
        { icon: GitBranch, label: 'Trigger agents on push and pull request events' },
        { icon: Webhook, label: 'Receive webhooks scoped to a single repository' },
        { icon: Lock, label: 'Read-only access — no write permissions required' },
      ].map(({ icon: Icon, label }) => (
        <li key={label} className="flex items-center gap-2">
          <Icon className="size-3.5 shrink-0 text-muted-foreground/60" />
          <span>{label}</span>
        </li>
      ))}
    </ul>
  )

  const renderAction = () => {
    if (!installUrl) {
      return (
        <div className="border border-dashed border-amber-500/40 bg-amber-500/5 px-3 py-2 text-[11px] font-mono text-amber-400">
          VITE_GITHUB_APP_SLUG is not configured — set it in your .env.local to enable GitHub connect.
        </div>
      )
    }
    return (
      <Button
        size="xs"
        className="rounded-none gap-1.5"
        onClick={() => {
                if (project) {
                  localStorage.setItem(PROJECT_SESSION_KEY, JSON.stringify({ projectId: project.id, projectSlug }))
                }
                window.location.href = installUrl
              }}
      >
        <GitFork className="size-3.5" />
        Install GitHub App
      </Button>
    )
  }

  const renderContent = () => (
    <div className="flex min-h-screen items-center justify-center bg-background p-8">
      <div className="w-full max-w-md border border-dashed border-border/60">
        {/* header strip */}
        <div className="flex items-center gap-3 border-b border-dashed border-border/60 px-4 py-3">
          <div className="w-[3px] self-stretch bg-muted-foreground/30" />
          <GitFork className="size-4 text-muted-foreground/60" />
          <div>
            <p className="text-[10px] font-mono tracking-widest text-muted-foreground/50 uppercase">
              {project?.name ?? projectSlug}
            </p>
            <p className="text-sm font-mono font-medium leading-tight">Connect your GitHub repo</p>
          </div>
        </div>

        {/* body */}
        <div className="space-y-4 px-4 py-4">
          <p className="text-[13px] text-muted-foreground leading-relaxed">
            Link a GitHub repository to this project so Zenve agents can respond to code events.
            Install the GitHub App and authorize it on any repo you own.
          </p>

          <div className="border border-dashed border-border/60 px-3 py-3">
            <p className="mb-2 text-[10px] font-mono tracking-widest text-muted-foreground/50 uppercase">
              What this enables
            </p>
            {renderChecklist()}
          </div>
        </div>

        {/* toolbar */}
        <div className="flex items-center border-t border-dashed border-border/60 bg-muted/30 px-4 py-2">
          {renderAction()}
        </div>
      </div>
    </div>
  )

  // --- return ---
  return renderContent()
}
