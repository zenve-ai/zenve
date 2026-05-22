import { IntegrationsSettings } from '@/components/settings'

export default function SettingsIntegrationsPage() {
  return (
    <div className="mx-auto max-w-2xl px-8 py-8">
      <h2 className="mb-1 text-[15px] font-semibold tracking-tight">Integrations</h2>
      <p className="mb-6 font-mono text-[11px] text-muted-foreground/50">GitHub and API key connections.</p>
      <IntegrationsSettings />
    </div>
  )
}
