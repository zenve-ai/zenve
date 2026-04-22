import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  OnboardingDecorativePanel,
  OnboardingStepIndicator,
  StepProjectName,
  StepGithubConnect,
  StepSelectAgents,
  StepFinish,
} from '@/components/onboarding'

const TOTAL_STEPS = 4

export default function OnboardingPage() {
  // --- declarations ---
  const [currentStep, setCurrentStep] = useState(0)
  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [nameError, setNameError] = useState<string | null>(null)
  const [githubStatus, setGithubStatus] = useState<'idle' | 'connected'>('idle')
  const [selectedAgents, setSelectedAgents] = useState<Set<string>>(new Set())

  const isLastStep = currentStep === TOTAL_STEPS - 1

  // --- render helpers ---
  const handleNext = () => {
    if (currentStep === 0) {
      if (!projectName.trim()) {
        setNameError('Project name is required.')
        return
      }
      setNameError(null)
    }
    setCurrentStep((s) => Math.min(s + 1, TOTAL_STEPS - 1))
  }

  const handleBack = () => {
    setCurrentStep((s) => Math.max(s - 1, 0))
    setNameError(null)
  }

  const handleToggleAgent = (id: string) => {
    setSelectedAgents((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
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
            githubStatus={githubStatus}
            onToggle={() => setGithubStatus((s) => s === 'connected' ? 'idle' : 'connected')}
          />
        )
      case 2:
        return (
          <StepSelectAgents
            selectedAgents={selectedAgents}
            onToggle={handleToggleAgent}
          />
        )
      case 3:
        return (
          <StepFinish
            projectName={projectName}
            projectDescription={projectDescription}
            githubStatus={githubStatus}
            selectedAgentCount={selectedAgents.size}
          />
        )
      default:
        return null
    }
  }

  const renderFooter = () => {
    if (isLastStep) return null
    return (
      <div className="flex items-center justify-between border-t border-dashed border-border/60 px-8 py-4 bg-muted/10">
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
