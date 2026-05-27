import { useMemo } from 'react'
import { useParams } from 'react-router'
import { CircleDot, GitPullRequest, Server, Settings, Users } from 'lucide-react'
import { NavMain, type NavGroup } from './nav-main'
import { NavUser } from './nav-user'
import { WorkspaceSwitcher } from './workspace-switcher'
import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader } from '@/components/ui/sidebar'

export function AppSidebar(props: React.ComponentProps<typeof Sidebar>) {
  const { workspaceId } = useParams<{ workspaceId: string }>()

  const navGroups = useMemo((): NavGroup[] => {
    const prefix = workspaceId ? `/${workspaceId}` : ''
    return [
      {
        label: 'Workspace',
        items: [
          { title: 'Agents', url: `${prefix}/agents`, icon: Users },
          { title: 'Issues', url: `${prefix}/issues`, icon: CircleDot },
          { title: 'Pull Requests', url: `${prefix}/pull-requests`, icon: GitPullRequest },
        ],
      },
      {
        label: 'Configure',
        items: [
          { title: 'Runtime', url: `${prefix}/runtime`, icon: Server },
          { title: 'Settings', url: `${prefix}/settings`, icon: Settings },
        ],
      },
    ]
  }, [workspaceId])

  return (
    <Sidebar variant="inset" {...props}>
      <SidebarHeader>
        <WorkspaceSwitcher />
      </SidebarHeader>
      <SidebarContent>
        <NavMain groups={navGroups} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
    </Sidebar>
  )
}
