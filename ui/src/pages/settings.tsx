import { Navigate, Outlet, useParams } from 'react-router'
import { SettingsSidebar } from '@/components/settings'

export default function SettingsPage() {
  return (
    <div className="flex h-full overflow-hidden">
      <div className="w-[200px] shrink-0 overflow-y-auto border-r border-dashed border-border/60 bg-muted/10">
        <SettingsSidebar />
      </div>
      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  )
}

export function SettingsRedirect() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  return <Navigate to={`/${workspaceId}/settings/profile`} replace />
}
