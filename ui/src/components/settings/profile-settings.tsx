import { SettingsSection } from './settings-section'
import { SettingsItem } from './settings-item'
import { useAppSelector } from '@/store/hooks'
import { selectCurrentUser } from '@/store/auth'
import { User, Mail } from 'lucide-react'

export function ProfileSettings() {
  const user = useAppSelector(selectCurrentUser)

  return (
    <div className="flex flex-col gap-6">
      <p className="font-mono text-[11px] leading-relaxed text-muted-foreground/60">
        Your identity as registered with this Zenve instance. Profile details are managed by your authentication provider.
      </p>

      <SettingsSection label="Identity">
        <SettingsItem
          icon={<User className="h-3.5 w-3.5 text-muted-foreground/60" />}
          title={user?.name || 'No name set'}
          description="Display name"
        />
        <SettingsItem
          icon={<Mail className="h-3.5 w-3.5 text-muted-foreground/60" />}
          title={user?.email || '—'}
          description="Email address"
        />
      </SettingsSection>
    </div>
  )
}
