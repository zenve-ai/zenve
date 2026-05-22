import { Link, useLocation } from 'react-router'
import { useParams } from 'react-router'
import { User, Building2, Plug, TriangleAlert, Globe, GitFork } from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  id: string
  title: string
  icon: React.ElementType
  disabled?: boolean
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const groups: NavGroup[] = [
  {
    label: 'Account',
    items: [
      { id: 'profile', title: 'Profile', icon: User },
      { id: 'global', title: 'Global', icon: Globe },
    ],
  },
  {
    label: 'Workspace',
    items: [
      { id: 'general', title: 'General', icon: Building2 },
      { id: 'pipeline', title: 'Pipeline', icon: GitFork },
      { id: 'integrations', title: 'Integrations', icon: Plug },
      { id: 'danger', title: 'Danger Zone', icon: TriangleAlert },
    ],
  },
]

export function SettingsSidebar() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const { pathname } = useLocation()

  return (
    <nav className="flex flex-col gap-4 p-3">
      {groups.map((group) => (
        <div key={group.label}>
          <p className="mb-1 px-2 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50 uppercase">
            {group.label}
          </p>
          <div className="flex flex-col gap-0.5">
            {group.items.map((item) => {
              const href = `/${workspaceId}/settings/${item.id}`
              const isActive = pathname === href || pathname.startsWith(href + '/')
              const Icon = item.icon
              return (
                <Link
                  key={item.id}
                  to={item.disabled ? '#' : href}
                  aria-disabled={item.disabled}
                  className={cn(
                    'flex items-center gap-2.5 px-2 py-1.5 text-[13px] transition-colors',
                    'hover:bg-muted/40',
                    isActive && 'bg-muted/60 font-medium',
                    item.disabled && 'pointer-events-none opacity-40',
                    item.id === 'danger' && 'text-destructive/80 hover:text-destructive',
                  )}
                >
                  <Icon className="h-3.5 w-3.5 shrink-0" />
                  <span>{item.title}</span>
                </Link>
              )
            })}
          </div>
        </div>
      ))}
    </nav>
  )
}
