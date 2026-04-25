import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import {
  OnboardingDecorativePanel,
  OnboardingStepIndicator,
  StepProjectName,
  StepGithubConnect,
  StepSelectAgents,
  StepFinish,
} from '@/components/onboarding'
import { useCreateProjectMutation, useConnectGithubMutation, useInitProjectMutation } from '@/store/project'
import { useListTemplatesQuery } from '@/store/agents'
import config from '@/config'

const TOTAL_STEPS = 4
const SESSION_KEY = 'zenve_onboarding_session'

interface OnboardingSession {
  projectName: string
  projectDescription: string
  selectedRepo?: string
}

export default function OnboardingPage() {
  // --- declarations ---
  const { step } = useParams<{ step: string }>()
  const navigate = useNavigate()
  const currentStep = Math.max(0, Math.min(parseInt(step ?? '1', 10) - 1, TOTAL_STEPS - 1))
  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [nameError, setNameError] = useState<string | null>(null)
  const [finishError, setFinishError] = useState<string | null>(null)
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)
  const [selectedAgents, setSelectedAgents] = useState<Set<string>>(new Set())
  const { data: templates = [], isLoading: isLoadingTemplates } = useListTemplatesQuery()
  const [createProject, { isLoading: isCreating }] = useCreateProjectMutation()
  const [connectGithub, { isLoading: isConnecting }] = useConnectGithubMutation()
  const [initProject, { isLoading: isIniting }] = useInitProjectMutation()

  const isLastStep = currentStep === TOTAL_STEPS - 1

  const callbackUrl = `${window.location.origin}/github/callback`
  const installUrl = config.githubAppSlug
    ? `https://github.com/apps/${config.githubAppSlug}/installations/new?redirect_url=${encodeURIComponent(callbackUrl)}`
    : null

  // --- effects ---
  useEffect(() => {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return
    try {
      const session: OnboardingSession = JSON.parse(raw)
      setProjectName(session.projectName)
      setProjectDescription(session.projectDescription)
      if (session.selectedRepo) setSelectedRepo(session.selectedRepo)
    } catch {
      // ignore malformed session
    }
    localStorage.removeItem(SESSION_KEY)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // --- render helpers ---
  const handleNext = () => {
    if (currentStep === 0) {
      if (!projectName.trim()) {
        setNameError('Project name is required.')
        return
      }
      setNameError(null)
    }

    navigate(`/onboarding/${currentStep + 2}`)
  }

  const handleBack = () => {
    setNameError(null)
    setFinishError(null)
    navigate(`/onboarding/${currentStep}`)
  }

  const handleToggleAgent = (id: string) => {
    setSelectedAgents((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleConnectClick = () => {
    if (!installUrl) return
    const session: OnboardingSession = {
      projectName,
      projectDescription,
    }
    localStorage.setItem(SESSION_KEY, JSON.stringify(session))
    window.location.href = installUrl
  }

  const handleFinish = async () => {
    setFinishError(null)
    const r1 = await createProject({ name: projectName.trim() })
    if ('error' in r1) {
      const err = r1.error
      const detail = 'data' in err
        ? String((err.data as Record<string, unknown>)?.detail ?? 'Failed to create project')
        : 'Failed to create project'
      setFinishError(detail)
      return
    }
    const { id, slug } = r1.data
    if (selectedRepo) {
      const r2 = await connectGithub({ projectId: id, repo: selectedRepo })
      if ('error' in r2) {
        const err = r2.error
        const detail = 'data' in err
          ? String((err.data as Record<string, unknown>)?.detail ?? 'Failed to connect repository')
          : 'Failed to connect repository'
        setFinishError(detail)
        return
      }

      const agentSpecs = Array.from(selectedAgents).map((templateId) => {
        const t = templates.find((a) => a.id === templateId)!
        return { name: t.name, template: t.id }
      })
      const r3 = await initProject({
        projectId: id,
        body: { description: projectDescription.trim() || undefined, agents: agentSpecs },
      })
      if ('error' in r3) {
        const err = r3.error
        const detail = 'data' in err
          ? String((err.data as Record<string, unknown>)?.detail ?? 'Failed to initialize project')
          : 'Failed to initialize project'
        setFinishError(detail)
        return
      }
    }
    navigate(`/${slug}`)
  }

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return (
          <StepProjectName
            projectName={projectName}
            projectDescription={projectDescription}
            nameError={nameError}
            onNameChange={setProjectName}
            onDescriptionChange={setProjectDescription}
          />
        )
      case 1:
        return (
          <StepGithubConnect
            selectedRepo={selectedRepo}
            installUrl={installUrl}
            onRepoSelected={setSelectedRepo}
            onConnectClick={handleConnectClick}
          />
        )
      case 2:
        return (
          <StepSelectAgents
            templates={templates}
            isLoading={isLoadingTemplates}
            selectedAgents={selectedAgents}
            onToggle={handleToggleAgent}
          />
        )
      case 3:
        return (
          <StepFinish
            projectName={projectName}
            projectDescription={projectDescription}
            githubRepo={selectedRepo}
            selectedAgentCount={selectedAgents.size}
            onGetStarted={handleFinish}
            isLoading={isCreating || isConnecting || isIniting}
            error={finishError}
          />
        )
      default:
        return null
    }
  }

  const renderFooter = () => {
    if (isLastStep) return null
    return (
      <div className="flex flex-col border-t border-dashed border-border/60 bg-muted/10">
        <div className="flex items-center justify-between px-8 py-4">
          <Button
            size="xs"
            variant="ghost"
            className={`rounded-none ${currentStep === 0 ? 'invisible' : ''}`}
            onClick={handleBack}
          >
            Back
          </Button>
          <Button
            size="xs"
            className="rounded-none"
            onClick={handleNext}
          >
            Next
          </Button>
        </div>
      </div>
    )
  }

  const renderLeft = () => (
    <div className="flex flex-col w-1/2 border-r border-dashed border-border/60 min-h-svh">
      {/* logo strip */}
      <div className="flex items-center gap-2 border-b border-dashed border-border/60 px-8 py-4">
        <span className="font-mono text-[11px] tracking-widest uppercase font-semibold">ZENVE</span>
        <span className="font-mono text-[10px] text-muted-foreground/40 tracking-widest uppercase">
          | Setup
        </span>
      </div>

      {/* step indicator */}
      <div className="border-b border-dashed border-border/60">
        <OnboardingStepIndicator currentStep={currentStep} />
      </div>

      {/* step content */}
      <div className="flex-1 overflow-y-auto px-8 py-8">
        {renderStep()}
      </div>

      {/* footer */}
      {renderFooter()}
    </div>
  )

  const renderRight = () => (
    <div className="sticky top-0 h-screen w-1/2">
      <OnboardingDecorativePanel />
    </div>
  )

  // --- return ---
  return (
    <div className="flex min-h-svh bg-background">
      {renderLeft()}
      {renderRight()}
    </div>
  )
}
