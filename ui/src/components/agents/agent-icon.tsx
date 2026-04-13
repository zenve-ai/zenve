import { Code, Compass, Crown, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AgentIconKey } from '@/types'

const AGENT_ICONS: Record<AgentIconKey, LucideIcon> = {
  crown: Crown,
  compass: Compass,
  code: Code,
}

const ICON_KEYS: AgentIconKey[] = ['crown', 'compass', 'code']

export function assignIconKey(slug: string): AgentIconKey {
  let hash = 0
  for (let i = 0; i < slug.length; i++) {
    hash = (hash * 31 + slug.charCodeAt(i)) | 0
  }
  return ICON_KEYS[Math.abs(hash) % ICON_KEYS.length]
}

export function getAgentLucideIcon(slug: string): LucideIcon {
  return AGENT_ICONS[assignIconKey(slug)] ?? Code
}

export function AgentIcon({
  slug,
  className,
  iconClassName,
}: {
  slug: string
  className?: string
  iconClassName?: string
}) {
  const key = assignIconKey(slug)
  const IconCmp = AGENT_ICONS[key] ?? Code
  return (
    <div className={cn('flex shrink-0 items-center justify-center border border-border bg-muted/50', className)}>
      <IconCmp className={cn('size-3', iconClassName)} aria-hidden />
    </div>
  )
}
