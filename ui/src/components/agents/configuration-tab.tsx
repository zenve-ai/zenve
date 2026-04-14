import { JsonBlock } from '@/components/agents/json-block'
import { PlaceholderTab } from '@/components/agents/placeholder-tab'
import type { Agent } from '@/types'

export function ConfigurationTab({ agent }: { agent: Agent }) {
  return (
    <PlaceholderTab title="Adapter configuration">
      <JsonBlock value={agent.adapterConfig} />
    </PlaceholderTab>
  )
}
