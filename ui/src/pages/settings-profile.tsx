import { ProfileSettings } from '@/components/settings'

export default function SettingsProfilePage() {
  return (
    <div className="mx-auto max-w-2xl px-8 py-8">
      <h2 className="mb-1 text-[15px] font-semibold tracking-tight">Profile</h2>
      <p className="mb-6 font-mono text-[11px] text-muted-foreground/50">Your account identity.</p>
      <ProfileSettings />
    </div>
  )
}
