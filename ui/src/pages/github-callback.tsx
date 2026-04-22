import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router'
import { GitFork, AlertTriangle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useSaveGithubInstallationMutation, useConnectGithubMutation, useListGithubReposQuery } from '@/store/project'

const ONBOARDING_SESSION_KEY = 'zenve_onboarding_session'
const PROJECT_SESSION_KEY = 'zenve_project_session'

interface OnboardingSession {
  projectName: string
  projectDescription: string
  selectedRepo?: string
}

interface ProjectSession {
  projectId: string
  projectSlug: string
}

export default function GitHubCallback() {
  // --- declarations ---
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [repo, setRepo] = useState('')
  const [installationSaved, setInstallationSaved] = useState(false)
  const [saveGithubInstallation, { isLoading: isSaving, error: saveError }] = useSaveGithubInstallationMutation()
  const [connectGithub, { isLoading: isConnecting, error: connectError }] = useConnectGithubMutation()

  const rawInstallationId = searchParams.get('installation_id')
  const installationId = rawInstallationId ? parseInt(rawInstallationId, 10) : null
  const isInvalidId = installationId === null || isNaN(installationId)

  let onboardingSession: OnboardingSession | null = null
  let projectSession: ProjectSession | null = null
  try {
    const raw = localStorage.getItem(ONBOARDING_SESSION_KEY)
    if (raw) onboardingSession = JSON.parse(raw)
  } catch { /* ignore */ }
  try {
    const raw = localStorage.getItem(PROJECT_SESSION_KEY)
    if (raw) projectSession = JSON.parse(raw)
  } catch { /* ignore */ }

  const isOnboardingFlow = onboardingSession !== null
  const isInvalid = isInvalidId || (isOnboardingFlow ? onboardingSession === null : projectSession === null)
  const successRedirect = isOnboardingFlow ? '/onboarding/2' : `/${projectSession?.projectSlug}`

  const { data: repos, isLoading: isLoadingRepos } = useListGithubReposQuery(
    undefined,
    { skip: !installationSaved }
  )

  const saveError_msg = saveError
    ? ('data' in saveError ? String((saveError.data as Record<string, unknown>)?.detail ?? 'Failed to save installation') : 'Failed to save installation')
    : null
  const connectError_msg = connectError
    ? ('data' in connectError ? String((connectError.data as Record<string, unknown>)?.detail ?? 'Failed to connect repository') : 'Failed to connect repository')
    : null

  // --- effects ---
  useEffect(() => {
    if (isInvalid || installationId === null) return
    saveGithubInstallation({ installationId }).then((result) => {
      if (!('error' in result)) setInstallationSaved(true)
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // --- render helpers ---
  const renderError = () => (
    <div className="flex min-h-screen items-center justify-center bg-background p-8">
      <div className="w-full max-w-md border border-dashed border-red-500/40">
        <div className="flex items-center gap-3 border-b border-dashed border-red-500/40 px-4 py-3">
          <AlertTriangle className="size-4 text-red-400" />
          <p className="text-sm font-mono font-medium text-red-400">Invalid callback</p>
        </div>
        <p className="px-4 py-4 text-[13px] font-mono text-muted-foreground">
          {isInvalidId
            ? <>No <span className="text-foreground">installation_id</span> was returned from GitHub.</>
            : <>No session found.</>
          }{' '}
          Please <Link to="/onboarding" className="text-foreground underline">start the setup flow again</Link>.
        </p>
      </div>
    </div>
  )

  const renderContent = () => (
    <div className="flex min-h-screen items-center justify-center bg-background p-8">
      <div className="w-full max-w-md border border-dashed border-border/60">
        {/* header */}
        <div className="flex items-center gap-3 border-b border-dashed border-border/60 px-4 py-3">
          <div className="w-[3px] self-stretch bg-emerald-500/60" />
          <GitFork className="size-4 text-muted-foreground/60" />
          <div>
            <p className="text-[10px] font-mono tracking-widest text-muted-foreground/50 uppercase">
              {isOnboardingFlow ? (onboardingSession?.projectName ?? 'New project') : projectSession?.projectSlug}
            </p>
            <p className="text-sm font-mono font-medium leading-tight">GitHub App installed</p>
          </div>
        </div>

        {/* body */}
        <div className="space-y-4 px-4 py-4">
          {/* save installation step */}
          {!installationSaved && (
            <div className="flex items-center gap-3">
              {saveError_msg ? (
                <div className="w-full border border-dashed border-red-500/40 bg-red-500/5 px-3 py-2 text-[11px] font-mono text-red-400">
                  {saveError_msg}{' '}
                  <Link to="/onboarding" className="underline">Try again</Link>.
                </div>
              ) : (
                <>
                  <Loader2 className={`size-4 shrink-0 text-muted-foreground/50 ${isSaving ? 'animate-spin' : ''}`} />
                  <p className="text-[13px] font-mono text-muted-foreground">Saving installation…</p>
                </>
              )}
            </div>
          )}

          {/* repo selection — shown after installation is saved */}
          {installationSaved && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-mono tracking-widest text-muted-foreground/50 uppercase">
                Repository
              </p>
              {isLoadingRepos ? (
                <div className="flex items-center gap-2 text-[13px] font-mono text-muted-foreground">
                  <Loader2 className="size-3.5 animate-spin text-muted-foreground/50" />
                  Loading repositories…
                </div>
              ) : (
                <Select value={repo} onValueChange={setRepo}>
                  <SelectTrigger className="rounded-none font-mono text-sm">
                    <SelectValue placeholder="Select a repository…" />
                  </SelectTrigger>
                  <SelectContent>
                    {repos?.map((r) => (
                      <SelectItem key={r.id} value={r.full_name} className="font-mono text-sm">
                        {r.full_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          )}

          {connectError_msg && (
            <div className="border border-dashed border-red-500/40 bg-red-500/5 px-3 py-2 text-[11px] font-mono text-red-400">
              {connectError_msg}
            </div>
          )}
        </div>

        {/* toolbar */}
        {installationSaved && (
          <div className="flex items-center border-t border-dashed border-border/60 bg-muted/30 px-4 py-2">
            <Button
              size="xs"
              className="rounded-none"
              disabled={isConnecting || !repo}
              onClick={async () => {
                if (isOnboardingFlow) {
                  localStorage.setItem(ONBOARDING_SESSION_KEY, JSON.stringify({ ...onboardingSession, selectedRepo: repo }))
                  navigate(successRedirect, { replace: true })
                  return
                }
                if (!projectSession || installationId === null) return
                const result = await connectGithub({ projectId: projectSession.projectId, installationId, repo })
                if (!('error' in result)) {
                  localStorage.removeItem(PROJECT_SESSION_KEY)
                  navigate(successRedirect, { replace: true })
                }
              }}
            >
              {isConnecting ? 'Connecting…' : 'Connect Repository'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )

  // --- compose ---
  const renderMain = () => {
    if (isInvalid) return renderError()
    return renderContent()
  }

  return renderMain()
}
