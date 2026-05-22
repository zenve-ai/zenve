import { cn } from '@/lib/utils'

interface SettingsItemProps {
  icon?: React.ReactNode
  title: string
  description?: React.ReactNode
  action?: React.ReactNode
  className?: string
}

export function SettingsItem({ icon, title, description, action, className }: SettingsItemProps) {
  return (
    <div className={cn('flex items-start gap-3.5 px-4 py-3.5', className)}>
      {icon && (
        <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center border border-dashed border-border-visible bg-muted/20">
          {icon}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-medium">{title}</p>
        {description && (
          <p className="mt-0.5 font-mono text-[11px] leading-relaxed text-muted-foreground/60">
            {description}
          </p>
        )}
      </div>
      {action && (
        <div className="mt-0.5 shrink-0">
          {action}
        </div>
      )}
    </div>
  )
}
