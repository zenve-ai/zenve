import type { OrganizationSummary } from '@/types'

/** Static catalog for UI-first multi-org; replace with API data later. */
export const MOCK_ORGANIZATIONS: OrganizationSummary[] = [
  {
    id: 'org-zapant',
    name: 'Zapant',
    slug: 'zapant',
    role: 'Owner',
    iconKey: 'zap',
  },
  {
    id: 'org-pretulmeu',
    name: 'PretulMeu',
    slug: 'pretulmeu',
    role: 'Owner',
    iconKey: 'triangle',
  },
  {
    id: 'org-demo',
    name: 'Demo',
    slug: 'demo',
    role: 'Admin',
    iconKey: 'box',
  },
  {
    id: 'org-primarie',
    name: 'Primarie',
    slug: 'primarie',
    role: 'Member',
    iconKey: 'cpu',
  },
  {
    id: 'org-logzai',
    name: 'LogzAI',
    slug: 'logzai',
    role: 'Owner',
    iconKey: 'layers',
  },
  {
    id: 'org-swapearn',
    name: 'SwapEarn',
    slug: 'swapearn',
    role: 'Admin',
    iconKey: 'building',
  },
]
