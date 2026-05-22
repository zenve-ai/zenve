import { PipelineSettings } from '@/components/settings'

export default function SettingsPipelinePage() {
  return (
    <div className="mx-auto max-w-2xl px-8 py-8">
      <h2 className="mb-1 text-[15px] font-semibold tracking-tight">Pipeline</h2>
      <p className="mb-6 font-mono text-[11px] text-muted-foreground/50">Agent label transitions for this workspace.</p>
      <PipelineSettings />
    </div>
  )
}
