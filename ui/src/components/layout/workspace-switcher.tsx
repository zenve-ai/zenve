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
import { selectCurrentWorkspace, selectWorkspaces, setCurrentWorkspace } from '@/store/workspace'
import type { WorkspaceIconKey } from '@/types'

const WORKSPACE_ICONS: Record<WorkspaceIconKey, LucideIcon> = {
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

export function WorkspaceSwitcher() {
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const workspaces = useAppSelector(selectWorkspaces)
  const current = useAppSelector(selectCurrentWorkspace)

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (!e.metaKey && !e.ctrlKey) return
      if (e.altKey || e.shiftKey) return
      if (isEditableTarget(e.target)) return
      const match = /^Digit([1-9])$/.exec(e.code)
      if (!match) return
      const index = Number(match[1]) - 1
      const workspace = workspaces[index]
      if (!workspace) return
      e.preventDefault()
      dispatch(setCurrentWorkspace(workspace.id))
      navigate(`/${workspace.id}`)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [dispatch, navigate, workspaces])

  if (!current) return null

  const CurrentIcon = WORKSPACE_ICONS[current.iconKey] ?? Box

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-gray-900 text-white">
                <CurrentIcon className="size-4" />
              </div>
              <div className="grid min-w-0 flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">{current.name}</span>
                <span className="truncate font-mono text-[10px] tracking-widest uppercase text-muted-foreground">
                  {current.agentCount} {current.agentCount === 1 ? 'agent' : 'agents'}
                </span>
              </div>
              <ChevronsUpDown className="ml-auto size-4 shrink-0 opacity-50" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-[--radix-dropdown-menu-trigger-width] min-w-56" align="start">
            <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
              Workspaces
            </DropdownMenuLabel>
            <DropdownMenuGroup>
              {workspaces.map((workspace, i) => {
                const Icon = WORKSPACE_ICONS[workspace.iconKey] ?? Box
                const shortcut = i < 9 ? `${MOD_SYMBOL}${i + 1}` : undefined
                return (
                  <DropdownMenuItem
                    key={workspace.id}
                    className="gap-2"
                    onSelect={() => {
                      dispatch(setCurrentWorkspace(workspace.id))
                      navigate(`/${workspace.id}`)
                    }}
                  >
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-md border bg-muted/40">
                      <Icon className="size-4 text-muted-foreground" />
                    </div>
                    <div className="grid min-w-0 flex-1 leading-tight">
                      <span className="truncate">{workspace.name}</span>
                      <span className="truncate font-mono text-[10px] tracking-widest uppercase text-muted-foreground">
                        {workspace.agentCount} {workspace.agentCount === 1 ? 'agent' : 'agents'}
                      </span>
                    </div>
                    {shortcut ? <DropdownMenuShortcut>{shortcut}</DropdownMenuShortcut> : null}
                  </DropdownMenuItem>
                )
              })}
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="gap-2" onSelect={() => navigate('/onboarding')}>
              <div className="flex size-8 shrink-0 items-center justify-center rounded-md border bg-muted/40">
                <Plus className="size-4 text-muted-foreground" />
              </div>
              <span>Create workspace</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
