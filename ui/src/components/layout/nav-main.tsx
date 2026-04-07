import { useState } from 'react'
import { Link, useLocation } from 'react-router'
import { ChevronRight, type LucideIcon } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from '@/components/ui/sidebar'

export interface NavItem {
  title: string
  url: string
  icon: LucideIcon
  isActive?: boolean
  /** When set, submenu stays open while `location.pathname` includes this substring (e.g. `/agents`). */
  openWhenPathIncludes?: string
  items?: { title: string; url: string }[]
}

export function NavMain({ items }: { items: NavItem[] }) {
  const { pathname } = useLocation()

  return (
    <SidebarGroup>
      <SidebarGroupLabel>Platform</SidebarGroupLabel>
      <SidebarMenu>
        {items.map((item) => (
          <NavMainCollapsibleItem key={item.title} item={item} pathname={pathname} />
        ))}
      </SidebarMenu>
    </SidebarGroup>
  )
}

function NavMainCollapsibleItem({ item, pathname }: { item: NavItem; pathname: string }) {
  const forcedOpen = item.openWhenPathIncludes ? pathname.includes(item.openWhenPathIncludes) : false
  const [userOpen, setUserOpen] = useState(item.isActive ?? false)
  const open = forcedOpen ? true : userOpen

  return (
    <Collapsible
      asChild
      open={open}
      onOpenChange={(next) => {
        if (!forcedOpen) setUserOpen(next)
      }}
    >
      <SidebarMenuItem>
        <SidebarMenuButton asChild tooltip={item.title}>
          <Link to={item.url}>
            <item.icon />
            <span>{item.title}</span>
          </Link>
        </SidebarMenuButton>
        {item.items?.length ? (
          <>
            <CollapsibleTrigger asChild>
              <SidebarMenuAction className="data-[state=open]:rotate-90">
                <ChevronRight />
                <span className="sr-only">Toggle</span>
              </SidebarMenuAction>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <SidebarMenuSub>
                {item.items.map((subItem) => (
                  <SidebarMenuSubItem key={subItem.title}>
                    <SidebarMenuSubButton asChild>
                      <Link to={subItem.url}>
                        <span>{subItem.title}</span>
                      </Link>
                    </SidebarMenuSubButton>
                  </SidebarMenuSubItem>
                ))}
              </SidebarMenuSub>
            </CollapsibleContent>
          </>
        ) : null}
      </SidebarMenuItem>
    </Collapsible>
  )
}
