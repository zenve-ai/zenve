import { cn } from '@/lib/utils'

interface SettingsSectionProps {
  label?: string
  children: React.ReactNode
  className?: string
}

export function SettingsSection({ label, children, className }: SettingsSectionProps) {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {label && (
        <p className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50 uppercase">
          {label}
        </p>
      )}
      <div className="border border-dashed border-border-visible divide-y divide-dashed divide-border-visible">
        {children}
      </div>
    </div>
  )
}
