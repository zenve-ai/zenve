import { useParams } from 'react-router'
import { ArrowRight } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { SettingsSection } from './settings-section'
import { SettingsItem } from './settings-item'
import { useGetWorkspaceSettingsQuery } from '@/store/workspace'

function SkeletonItem() {
  return (
    <div className="flex items-center gap-3.5 px-4 py-3.5">
      <Skeleton className="size-8 shrink-0 rounded-none" />
      <div className="flex flex-1 flex-col gap-1.5">
        <Skeleton className="h-3.5 w-40 rounded-none" />
        <Skeleton className="h-3 w-24 rounded-none" />
      </div>
    </div>
  )
}

export function PipelineSettings() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const { data: settings, isLoading } = useGetWorkspaceSettingsQuery(workspaceId!, { skip: !workspaceId })

  const pipeline = settings?.pipeline ?? {}
  const isEmpty = Object.keys(pipeline).length === 0

  const renderLoading = () => (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-4 w-2/3 rounded-none" />
      <div className="border border-dashed border-border-visible divide-y divide-dashed divide-border-visible">
        <SkeletonItem />
        <SkeletonItem />
        <SkeletonItem />
      </div>
    </div>
  )

  const renderEmpty = () => (
    <p className="font-mono text-[11px] text-muted-foreground/50">
      No pipeline configured. Add a <span className="text-foreground/70">pipeline</span> key to <span className="text-foreground/70">.zenve/settings.json</span>.
    </p>
  )

  const renderPipeline = () => (
    <SettingsSection label="Transitions">
      {Object.entries(pipeline).map(([from, to]) => (
        <SettingsItem
          key={from}
          icon={<ArrowRight className="h-3.5 w-3.5 text-muted-foreground/60" />}
          title={from}
          description={to ?? 'end of pipeline'}
        />
      ))}
    </SettingsSection>
  )

  const renderMain = () => {
    if (isLoading) return renderLoading()
    return (
      <div className="flex flex-col gap-6">
        <p className="font-mono text-[11px] leading-relaxed text-muted-foreground/60">
          Label-to-label transitions defined in <span className="text-foreground/70">.zenve/settings.json</span>. Edit the file directly to change the pipeline.
        </p>
        {isEmpty ? renderEmpty() : renderPipeline()}
      </div>
    )
  }

  return renderMain()
}
