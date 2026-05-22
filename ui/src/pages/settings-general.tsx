import { WorkspaceSettings } from '@/components/settings'

export default function SettingsGeneralPage() {
  return (
    <div className="mx-auto max-w-2xl px-8 py-8">
      <h2 className="mb-1 text-[15px] font-semibold tracking-tight">General</h2>
      <p className="mb-6 font-mono text-[11px] text-muted-foreground/50">Workspace configuration from your .zenve/ config.</p>
      <WorkspaceSettings />
    </div>
  )
}
