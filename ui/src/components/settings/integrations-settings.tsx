import { useParams } from 'react-router'
import { SettingsSection } from './settings-section'
import { SettingsItem } from './settings-item'
import { useGetWorkspaceQuery } from '@/store/workspace'
import { GitFork, Key, GitBranch } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

function SkeletonItem() {
  return (
    <div className="flex items-center gap-3.5 px-4 py-3.5">
      <Skeleton className="size-8 shrink-0 rounded-none" />
      <div className="flex flex-1 flex-col gap-1.5">
        <Skeleton className="h-3.5 w-32 rounded-none" />
        <Skeleton className="h-3 w-56 rounded-none" />
      </div>
    </div>
  )
}

export function IntegrationsSettings() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const { data: ws, isLoading } = useGetWorkspaceQuery(workspaceId!, { skip: !workspaceId })

  const isGitHubConnected = Boolean(ws?.repo)

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-4 w-2/3 rounded-none" />
        <div className="border border-dashed border-border-visible divide-y divide-dashed divide-border-visible">
          <SkeletonItem />
          <SkeletonItem />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="font-mono text-[11px] leading-relaxed text-muted-foreground/60">
        External services connected to this workspace. GitHub integration is configured via your <span className="text-foreground/70">.zenve/config.yml</span>.
      </p>

      <SettingsSection label="GitHub">
        <SettingsItem
          icon={<GitFork className="h-3.5 w-3.5 text-muted-foreground/60" />}
          title="GitHub Repository"
          description={
            isGitHubConnected
              ? `Connected to ${ws!.repo}`
              : 'No repository linked. Set the repo field in .zenve/config.yml to connect.'
          }
          action={
            isGitHubConnected ? (
              <span className="flex items-center gap-1.5 font-mono text-[10px] font-bold tracking-widest text-emerald-500 uppercase">
                <span className="size-1.5 rounded-full bg-emerald-500" />
                Connected
              </span>
            ) : (
              <span className="flex items-center gap-1.5 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/40 uppercase">
                Not connected
              </span>
            )
          }
        />
        {isGitHubConnected && (
          <SettingsItem
            icon={<GitBranch className="h-3.5 w-3.5 text-muted-foreground/60" />}
            title={ws!.defaultBranch || 'main'}
            description="Default branch for PR submissions"
          />
        )}
      </SettingsSection>

      <SettingsSection label="API Access">
        <SettingsItem
          icon={<Key className="h-3.5 w-3.5 text-muted-foreground/60" />}
          title="API Keys"
          description="Manage API keys for programmatic access to agents and runs."
          action={
            <Button variant="outline" size="xs" className="rounded-none" disabled>
              Manage keys
            </Button>
          }
        />
      </SettingsSection>
    </div>
  )
}
