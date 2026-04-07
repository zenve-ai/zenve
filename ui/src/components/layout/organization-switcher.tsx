import { useEffect } from 'react'
import { useNavigate } from 'react-router'
import {
  Box,
  Building2,
  ChevronsUpDown,
  Cpu,
  Layers,
  Plus,
  Triangle,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem } from '@/components/ui/sidebar'
import { useAppDispatch, useAppSelector } from '@/store/hooks'
import {
  selectCurrentOrganization,
  selectOrganizations,
  setCurrentOrganization,
} from '@/store/organization'
import type { OrganizationIconKey } from '@/types'

const ORG_ICONS: Record<OrganizationIconKey, LucideIcon> = {
  zap: Zap,
  triangle: Triangle,
  box: Box,
  cpu: Cpu,
  building: Building2,
  layers: Layers,
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true
  if (target.isContentEditable) return true
  return false
}

const MOD_SYMBOL =
  typeof navigator !== 'undefined' && /Mac|iPhone|iPad|iPod/.test(navigator.platform)
    ? '⌘'
    : 'Ctrl+'

export function OrganizationSwitcher() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const organizations = useAppSelector(selectOrganizations)
  const current = useAppSelector(selectCurrentOrganization)

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (!e.metaKey && !e.ctrlKey) return
      if (e.altKey || e.shiftKey) return
      if (isEditableTarget(e.target)) return
      const match = /^Digit([1-9])$/.exec(e.code)
      if (!match) return
      const index = Number(match[1]) - 1
      const org = organizations[index]
      if (!org) return
      e.preventDefault()
      dispatch(setCurrentOrganization(org.id))
      navigate(`/${org.slug}`)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [dispatch, navigate, organizations])

  if (!current) return null

  const CurrentIcon = ORG_ICONS[current.iconKey] ?? Box

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg border border-sidebar-border bg-sidebar text-sidebar-foreground">
                <CurrentIcon className="size-4" />
              </div>
              <div className="grid min-w-0 flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">{current.name}</span>
                <span className="truncate text-xs text-muted-foreground">{current.role}</span>
              </div>
              <ChevronsUpDown className="ml-auto size-4 shrink-0 opacity-50" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-[--radix-dropdown-menu-trigger-width] min-w-56" align="start">
            <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
              Organizations
            </DropdownMenuLabel>
            <DropdownMenuGroup>
              {organizations.map((org, i) => {
                const Icon = ORG_ICONS[org.iconKey] ?? Box
                const shortcut = i < 9 ? `${MOD_SYMBOL}${i + 1}` : undefined
                return (
                  <DropdownMenuItem
                    key={org.id}
                    className="gap-2"
                    onSelect={() => {
                      dispatch(setCurrentOrganization(org.id))
                      navigate(`/${org.slug}`)
                    }}
                  >
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-md border bg-muted/40">
                      <Icon className="size-4 text-muted-foreground" />
                    </div>
                    <span className="min-w-0 flex-1 truncate">{org.name}</span>
                    {shortcut ? <DropdownMenuShortcut>{shortcut}</DropdownMenuShortcut> : null}
                  </DropdownMenuItem>
                )
              })}
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="gap-2" onSelect={() => navigate('/create-organization')}>
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md border bg-muted/40">
                <Plus className="size-4 text-muted-foreground" />
              </div>
              <span>Create organization</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
