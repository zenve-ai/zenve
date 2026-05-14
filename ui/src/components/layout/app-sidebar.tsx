import { useMemo } from 'react'
import { useParams } from 'react-router'
import { BookOpen, Bot, Settings2, Users } from 'lucide-react'
import { useListAgentsQuery } from '@/store/agents'
import { NavMain, type NavItem } from './nav-main'
import { NavUser } from './nav-user'
import { WorkspaceSwitcher } from './workspace-switcher'
import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader } from '@/components/ui/sidebar'

const demoNavTail: NavItem[] = [
  {
    title: 'Models',
    url: '#',
    icon: Bot,
    items: [
      { title: 'Genesis', url: '#' },
      { title: 'Explorer', url: '#' },
      { title: 'Quantum', url: '#' },
    ],
  },
  {
    title: 'Documentation',
    url: '#',
    icon: BookOpen,
    items: [
      { title: 'Introduction', url: '#' },
      { title: 'Get Started', url: '#' },
      { title: 'Tutorials', url: '#' },
      { title: 'Changelog', url: '#' },
    ],
  },
  {
    title: 'Settings',
    url: '#',
    icon: Settings2,
    items: [
      { title: 'General', url: '#' },
      { title: 'Team', url: '#' },
      { title: 'Billing', url: '#' },
      { title: 'Limits', url: '#' },
    ],
  },
]

export function AppSidebar(props: React.ComponentProps<typeof Sidebar>) {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const { data: agents = [] } = useListAgentsQuery(
    { workspaceId: workspaceId! },
    { skip: !workspaceId },
  )

  const navItems = useMemo((): NavItem[] => {
    const prefix = workspaceId ? `/${workspaceId}` : ''
    const agentsBlock: NavItem = {
      title: 'Agents',
      url: `${prefix}/agents`,
      icon: Users,
      openWhenPathIncludes: '/agents',
      items: agents.map((a) => ({
        title: a.name,
        url: `${prefix}/agents/${a.slug}`,
      })),
    }
    return [agentsBlock, ...demoNavTail]
  }, [workspaceId, agents])

  return (
    <Sidebar variant="inset" {...props}>
      <SidebarHeader>
        <WorkspaceSwitcher />
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={navItems} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
    </Sidebar>
  )
}
