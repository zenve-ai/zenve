import { Check, FolderOpen, GitFork, Bot, Flag } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'

interface OnboardingStepIndicatorProps {
  currentStep: number
}

const STEPS = [
  { label: 'Project', icon: FolderOpen },
  { label: 'GitHub', icon: GitFork },
  { label: 'Agents', icon: Bot },
  { label: 'Finish', icon: Flag },
]

export function OnboardingStepIndicator({ currentStep }: OnboardingStepIndicatorProps) {
  return (
    <Tabs value={currentStep.toString()} className="gap-0">
      <TabsList className="w-full h-auto border-b border-dashed border-border/60 bg-transparent p-0">
        {STEPS.map((step, index) => {
          const Icon = step.icon
          const completed = index < currentStep
          const active = index === currentStep
          return (
            <TabsTrigger
              key={index}
              value={index.toString()}
              disabled
              className={cn(
                'flex-1 gap-1.5 rounded-none border-b-2 px-3 py-2.5 text-[11px] font-mono tracking-widest uppercase',
                'disabled:pointer-events-none',
                active
                  ? 'border-foreground text-foreground opacity-100'
                  : completed
                    ? 'border-emerald-500/60 text-emerald-500 opacity-100'
                    : 'border-transparent text-muted-foreground/40 opacity-100',
              )}
            >
              {completed
                ? <Check className="size-3" />
                : <Icon className="size-3" />
              }
              {step.label}
            </TabsTrigger>
          )
        })}
      </TabsList>
    </Tabs>
  )
}
