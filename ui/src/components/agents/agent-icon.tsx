import {
  BarChart2,
  Bot,
  Code,
  Compass,
  Crown,
  FileText,
  GitPullRequest,
  Layers,
  Rocket,
  ShieldCheck,
  TestTube,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AgentIconKey } from '@/types'

const SLUG_KEYWORD_MAP: Array<[string[], LucideIcon]> = [
  [['architect', 'architecture'], Layers],
  [['frontend', 'ui', 'design', 'style'], Bot],
  [['backend', 'api', 'server'], Code],
  [['dev', 'code', 'coder', 'engineer'], Code],
  [['review', 'pr', 'pull-request', 'pullrequest'], GitPullRequest],
  [['deploy', 'ci', 'cd', 'pipeline', 'infra', 'devops', 'release'], Rocket],
  [['sec', 'security', 'audit', 'pentest'], ShieldCheck],
  [['doc', 'docs', 'writer', 'readme'], FileText],
  [['test', 'qa', 'quality'], TestTube],
  [['pm', 'product', 'manager', 'planning', 'planner'], BarChart2],
  [['fix', 'bug', 'debug', 'patch', 'maintenance'], Wrench],
  [['navigator', 'compass', 'lead'], Compass],
  [['owner', 'admin', 'boss', 'crown'], Crown],
]

const FALLBACK_ICONS: LucideIcon[] = [Bot, Code, Compass, Layers, Wrench, GitPullRequest]

function resolveIcon(slug: string): LucideIcon {
  const lower = slug.toLowerCase()
  for (const [keywords, icon] of SLUG_KEYWORD_MAP) {
    if (keywords.some((k) => lower.includes(k))) return icon
  }
  let hash = 0
  for (let i = 0; i < slug.length; i++) {
    hash = (hash * 31 + slug.charCodeAt(i)) | 0
  }
  return FALLBACK_ICONS[Math.abs(hash) % FALLBACK_ICONS.length]
}

export function assignIconKey(slug: string): AgentIconKey {
  const icon = resolveIcon(slug)
  if (icon === Crown) return 'crown'
  if (icon === Compass) return 'compass'
  return 'code'
}

export function getAgentLucideIcon(slug: string): LucideIcon {
  return resolveIcon(slug)
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
  const IconCmp = resolveIcon(slug)
  return (
    <div className={cn('flex shrink-0 items-center justify-center border border-border bg-muted/50', className)}>
      <IconCmp className={cn('size-3.5', iconClassName)} aria-hidden />
    </div>
  )
}
