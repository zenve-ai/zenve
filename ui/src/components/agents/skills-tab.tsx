import { PlaceholderTab } from '@/components/agents/placeholder-tab'
import type { Agent } from '@/types'

export function SkillsTab({ agent }: { agent: Agent }) {
  return (
    <PlaceholderTab title="Skills">
      {agent.skills.length === 0 ? (
        <span>No skills configured.</span>
      ) : (
        <ul className="mt-2 list-inside list-disc space-y-1 text-foreground">
          {agent.skills.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      )}
    </PlaceholderTab>
  )
}
