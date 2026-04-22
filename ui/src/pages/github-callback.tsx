import { useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router'
import { GitFork, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAppSelector } from '@/store/hooks'
import { selectCurrentProject, useConnectGithubMutation } from '@/store/project'

export default function GitHubCallback() {
  // --- declarations ---
  const { projectSlug } = useParams<{ projectSlug: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const project = useAppSelector(selectCurrentProject)
  const [repo, setRepo] = useState('')
  const [connectGithub, { isLoading, error }] = useConnectGithubMutation()

  const rawInstallationId = searchParams.get('installation_id')
  const installationId = rawInstallationId ? parseInt(rawInstallationId, 10) : null
  const isInvalid = installationId === null || isNaN(installationId)
  const errorMessage = error
    ? ('data' in error ? String((error.data as Record<string, unknown>)?.detail ?? 'Connection failed') : 'Connection failed')
    : null

  // --- render helpers ---
  const renderError = () => (
    <div className="flex min-h-screen items-center justify-center bg-background p-8">
      <div className="w-full max-w-md border border-dashed border-red-500/40">
        <div className="flex items-center gap-3 border-b border-dashed border-red-500/40 px-4 py-3">
          <AlertTriangle className="size-4 text-red-400" />
          <p className="text-sm font-mono font-medium text-red-400">Invalid callback</p>
        </div>
        <p className="px-4 py-4 text-[13px] font-mono text-muted-foreground">
          No <span className="text-foreground">installation_id</span> was returned from GitHub.
          Please start the setup flow again.
        </p>
      </div>
    </div>
  )

  const renderContent = () => (
    <div className="flex min-h-screen items-center justify-center bg-background p-8">
      <div className="w-full max-w-md border border-dashed border-border/60">
        {/* header strip */}
        <div className="flex items-center gap-3 border-b border-dashed border-border/60 px-4 py-3">
          <div className="w-[3px] self-stretch bg-emerald-500/60" />
          <GitFork className="size-4 text-muted-foreground/60" />
          <div>
            <p className="text-[10px] font-mono tracking-widest text-muted-foreground/50 uppercase">
              {project?.name ?? projectSlug}
            </p>
            <p className="text-sm font-mono font-medium leading-tight">GitHub App installed</p>
          </div>
        </div>

        {/* body */}
        <div className="space-y-4 px-4 py-4">
          {/* installation id badge */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono tracking-widest text-muted-foreground/50 uppercase">
              Installation ID
            </span>
            <span className="border border-dashed border-border/60 px-2 py-0.5 text-[11px] font-mono text-muted-foreground">
              {installationId}
            </span>
          </div>

          {/* repo input */}
          <div className="space-y-1.5">
            <p className="text-[10px] font-mono tracking-widest text-muted-foreground/50 uppercase">
              Repository
            </p>
            <Input
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="e.g. acme/my-project"
              className="rounded-none font-mono text-sm"
            />
            <p className="text-[11px] font-mono text-muted-foreground/50">
              Enter the repository in <span className="text-foreground/60">owner/name</span> format.
            </p>
          </div>

          {errorMessage && (
            <div className="border border-dashed border-red-500/40 bg-red-500/5 px-3 py-2 text-[11px] font-mono text-red-400">
              {errorMessage}
            </div>
          )}
        </div>

        {/* toolbar */}
        <div className="flex items-center border-t border-dashed border-border/60 bg-muted/30 px-4 py-2">
          <Button
            size="xs"
            className="rounded-none"
            disabled={isLoading || !repo.trim() || !project}
            onClick={async () => {
              if (!project || installationId === null) return
              const result = await connectGithub({ projectId: project.id, installationId, repo: repo.trim() })
              if (!('error' in result)) {
                navigate(`/${projectSlug}`, { replace: true })
              }
            }}
          >
            {isLoading ? 'Connecting…' : 'Connect Repository'}
          </Button>
        </div>
      </div>
    </div>
  )

  // --- main render ---
  const renderMain = () => {
    if (isInvalid) return renderError()
    return renderContent()
  }

  return renderMain()
}
