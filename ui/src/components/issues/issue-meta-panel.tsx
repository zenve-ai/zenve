import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn, relativeTime } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { IssueStateBadge } from './issue-state-badge'
import { LabelsEditor } from './labels-editor'
import type { Issue } from '@/types'

interface Props {
  issue: Issue
  onToggleState: () => void
  onUpdateLabels: (labels: string[]) => void
  isUpdating: boolean
}

function initials(name: string) {
  return name.trim().slice(0, 2).toUpperCase() || '?'
}

function Section({
  label,
  children,
  defaultOpen = true,
}: {
  label: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-b border-border/60">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-2.5 hover:bg-muted/20"
      >
        <span className="text-[13px] font-semibold">{label}</span>
        <ChevronDown
          className={cn(
            'size-3.5 text-muted-foreground/60 transition-transform',
            !open && '-rotate-90',
          )}
        />
      </button>
      {open && <div className="pb-1">{children}</div>}
    </div>
  )
}

function PropRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 px-4 py-1.5 hover:bg-muted/10">
      <span className="w-20 shrink-0 pt-0.5 font-mono text-[11px] text-muted-foreground/50">{label}</span>
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1">{children}</div>
    </div>
  )
}

export function IssueMetaPanel({ issue, onToggleState, onUpdateLabels, isUpdating }: Props) {
  return (
    <div className="flex flex-col text-sm">
      <Section label="Properties">
        <PropRow label="State">
          <div className="flex w-full items-center justify-between">
            <IssueStateBadge state={issue.state} />
            <Button
              variant="ghost"
              size="xs"
              className="rounded-none text-[10px] font-mono tracking-widest text-muted-foreground/60 hover:text-foreground"
              onClick={onToggleState}
              disabled={isUpdating}
            >
              {issue.state === 'open' ? 'CLOSE' : 'REOPEN'}
            </Button>
          </div>
        </PropRow>

        <PropRow label="Assignees">
          {issue.assignees.length === 0 ? (
            <span className="font-mono text-[11px] text-muted-foreground/30">No assignees</span>
          ) : (
            issue.assignees.map((a) => (
              <div key={a} className="flex items-center gap-1.5">
                <span
                  className="flex size-5 items-center justify-center bg-muted font-mono text-[9px] font-bold text-muted-foreground"
                  title={a}
                >
                  {initials(a)}
                </span>
                <span className="text-[12px]">{a}</span>
              </div>
            ))
          )}
        </PropRow>

        <PropRow label="Labels">
          <LabelsEditor
            labels={issue.labels}
            onUpdate={onUpdateLabels}
            disabled={isUpdating}
          />
        </PropRow>
      </Section>

      <Section label="Details">
        <PropRow label="Created">
          <span className="font-mono text-[11px] text-muted-foreground">
            {relativeTime(issue.createdAt)} ago
          </span>
        </PropRow>
        <PropRow label="Updated">
          <span className="font-mono text-[11px] text-muted-foreground">
            {relativeTime(issue.updatedAt)} ago
          </span>
        </PropRow>
        <PropRow label="ID">
          <span className="font-mono text-[11px] text-muted-foreground">
            #{String(issue.id).padStart(3, '0')}
          </span>
        </PropRow>
      </Section>
    </div>
  )
}
