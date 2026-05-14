import { cn } from '@/lib/utils'
import type { SkillTemplate } from '@/types'

interface StepSelectSkillsProps {
  skills: SkillTemplate[]
  isLoading: boolean
  selectedSkills: Set<string>
  onToggle: (id: string) => void
}

export function StepSelectSkills({ skills, isLoading, selectedSkills, onToggle }: StepSelectSkillsProps) {
  const renderSkillCard = (skill: SkillTemplate) => {
    const selected = selectedSkills.has(skill.id)
    return (
      <button
        key={skill.id}
        type="button"
        onClick={() => onToggle(skill.id)}
        className={cn(
          'flex items-stretch gap-0 border border-dashed text-left transition-colors',
          selected
            ? 'border-emerald-500/60 bg-emerald-500/5'
            : 'border-border/60 hover:border-border',
        )}
      >
        <div className={cn('w-[3px] shrink-0', selected ? 'bg-emerald-500' : 'bg-muted-foreground/20')} />
        <div className="flex flex-col gap-0.5 px-3 py-2.5">
          <span className="text-[11px] font-mono font-medium leading-tight">{skill.name}</span>
          <p className="text-[11px] text-muted-foreground leading-snug line-clamp-2">{skill.description}</p>
        </div>
      </button>
    )
  }

  const renderContent = () => {
    if (isLoading) {
      return (
        <p className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/40">
          Loading skills...
        </p>
      )
    }
    if (skills.length === 0) {
      return (
        <p className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/40">
          No skills available
        </p>
      )
    }
    return (
      <div className="grid grid-cols-2 gap-2">
        {skills.map(renderSkillCard)}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/50">
          Step 03 / 04
        </p>
        <h2 className="mt-1 text-lg font-semibold leading-tight">Select skills</h2>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Pick the skills to install for this workspace. Skills are shared across all agents.
        </p>
      </div>

      {renderContent()}

      {selectedSkills.size > 0 && (
        <p className="font-mono text-[10px] tracking-widest uppercase text-emerald-500">
          {selectedSkills.size} skill{selectedSkills.size !== 1 ? 's' : ''} selected
        </p>
      )}
    </div>
  )
}
