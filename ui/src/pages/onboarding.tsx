import { useState } from 'react'
import { useParams, useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import {
  OnboardingDecorativePanel,
  OnboardingStepIndicator,
  StepWorkspace,
  StepSelectAgents,
  StepSelectSkills,
  StepFinish,
} from '@/components/onboarding'
import { useScaffoldWorkspaceMutation } from '@/store/workspace'
import { useListTemplatesQuery, useListSkillsQuery } from '@/store/agents'

const TOTAL_STEPS = 4

export default function OnboardingPage() {
  const { step } = useParams<{ step: string }>()
  const navigate = useNavigate()
  const currentStep = Math.max(0, Math.min(parseInt(step ?? '1', 10) - 1, TOTAL_STEPS - 1))
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [path, setPath] = useState('')
  const [nameError, setNameError] = useState<string | null>(null)
  const [pathError, setPathError] = useState<string | null>(null)
  const [finishError, setFinishError] = useState<string | null>(null)
  const [selectedAgents, setSelectedAgents] = useState<Set<string>>(new Set())
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set())
  const [scaffoldWorkspace, { isLoading: isScaffolding }] = useScaffoldWorkspaceMutation()
  const { data: templates = [], isLoading: isLoadingTemplates } = useListTemplatesQuery()
  const { data: skills = [], isLoading: isLoadingSkills } = useListSkillsQuery()

  const isLastStep = currentStep === TOTAL_STEPS - 1

  const handleNext = () => {
    if (currentStep === 0) {
      let valid = true
      if (!name.trim()) {
        setNameError('Workspace name is required.')
        valid = false
      } else {
        setNameError(null)
      }
      if (!path.trim()) {
        setPathError('Path is required.')
        valid = false
      } else if (!path.startsWith('/')) {
        setPathError('Path must be absolute (start with /).')
        valid = false
      } else {
        setPathError(null)
      }
      if (!valid) return
    }

    navigate(`/onboarding/${currentStep + 2}`)
  }

  const handleBack = () => {
    setNameError(null)
    setPathError(null)
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

  const handleToggleSkill = (id: string) => {
    setSelectedSkills((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleFinish = async () => {
    setFinishError(null)
    const result = await scaffoldWorkspace({
      name: name.trim(),
      path: path.trim(),
      description: description.trim(),
      agents: Array.from(selectedAgents),
      skills: Array.from(selectedSkills),
    })
    if ('error' in result && result.error) {
      const err = result.error
      const detail = 'data' in err
        ? String((err.data as Record<string, unknown>)?.detail ?? 'Failed to create workspace')
        : 'Failed to create workspace'
      setFinishError(detail)
      return
    }
    if ('data' in result && result.data) {
      navigate(`/${result.data.id}`)
    }
  }

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return (
          <StepWorkspace
            name={name}
            description={description}
            path={path}
            nameError={nameError}
            pathError={pathError}
            onNameChange={setName}
            onDescriptionChange={setDescription}
            onPathChange={setPath}
          />
        )
      case 1:
        return (
          <StepSelectAgents
            templates={templates}
            isLoading={isLoadingTemplates}
            selectedAgents={selectedAgents}
            onToggle={handleToggleAgent}
          />
        )
      case 2:
        return (
          <StepSelectSkills
            skills={skills}
            isLoading={isLoadingSkills}
            selectedSkills={selectedSkills}
            onToggle={handleToggleSkill}
          />
        )
      case 3:
        return (
          <StepFinish
            name={name}
            description={description}
            path={path}
            selectedAgentCount={selectedAgents.size}
            selectedSkillCount={selectedSkills.size}
            onGetStarted={handleFinish}
            isLoading={isScaffolding}
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
          <Button size="xs" className="rounded-none" onClick={handleNext}>
            Next
          </Button>
        </div>
      </div>
    )
  }

  const renderLeft = () => (
    <div className="flex flex-col w-1/2 border-r border-dashed border-border/60 min-h-svh">
      <div className="flex items-center gap-2 border-b border-dashed border-border/60 px-8 py-4">
        <span className="font-mono text-[11px] tracking-widest uppercase font-semibold">ZENVE</span>
        <span className="font-mono text-[10px] text-muted-foreground/40 tracking-widest uppercase">
          | Setup
        </span>
      </div>

      <div className="border-b border-dashed border-border/60">
        <OnboardingStepIndicator currentStep={currentStep} />
      </div>

      <div className="flex-1 overflow-y-auto px-8 py-8">
        {renderStep()}
      </div>

      {renderFooter()}
    </div>
  )

  const renderRight = () => (
    <div className="sticky top-0 h-screen w-1/2">
      <OnboardingDecorativePanel />
    </div>
  )

  return (
    <div className="flex min-h-svh bg-background">
      {renderLeft()}
      {renderRight()}
    </div>
  )
}
