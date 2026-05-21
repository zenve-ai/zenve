import { useState } from 'react'
import { Loader2, Search, Server, Wifi, WifiOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useGetRuntimeInfoQuery, useListAdaptersQuery } from '@/store/runtime'
import type { AdapterItem, RuntimeInfo } from '@/types'
import { cn } from '@/lib/utils'

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

type HealthFilter = 'all' | 'online' | 'offline'

export default function RuntimesPage() {
  const [search, setSearch] = useState('')
  const [healthFilter, setHealthFilter] = useState<HealthFilter>('all')

  const { data: info, isLoading: infoLoading } = useGetRuntimeInfoQuery(undefined, {
    pollingInterval: 10000,
  })
  const { data: adapters = [], isLoading: adaptersLoading } = useListAdaptersQuery(undefined, {
    pollingInterval: 10000,
  })

  const isLoading = infoLoading || adaptersLoading

  const filteredAdapters = adapters.filter((a) => {
    const matchesSearch =
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.type.toLowerCase().includes(search.toLowerCase())
    const matchesHealth =
      healthFilter === 'all' ||
      (healthFilter === 'online' && a.healthy) ||
      (healthFilter === 'offline' && !a.healthy)
    return matchesSearch && matchesHealth
  })

  const onlineCount = adapters.filter((a) => a.healthy).length
  const offlineCount = adapters.filter((a) => !a.healthy).length

  const renderDaemonCard = (info: RuntimeInfo) => (
    <div className="border-b border-dashed border-border/60 bg-muted/10">
      <div className="flex items-center justify-between px-4 py-2.5">
        <div className="flex items-center gap-3">
          <Server className="size-4 text-muted-foreground" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold">Local daemon</span>
              <span className="flex items-center gap-1.5">
                <span className="size-1.5 rounded-full bg-emerald-500" />
                <span className="font-mono text-[10px] font-bold tracking-widest text-emerald-600">
                  RUNNING
                </span>
                <span className="font-mono text-[10px] text-muted-foreground/60">
                  · {formatUptime(info.uptimeSeconds)}
                </span>
              </span>
            </div>
            <p className="font-mono text-[10px] text-muted-foreground/60 mt-0.5">
              v{info.version} · PID {info.pid}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="xs" className="rounded-none font-mono text-[10px]">
            View logs
          </Button>
          <Button variant="ghost" size="xs" className="rounded-none font-mono text-[10px]">
            Restart
          </Button>
          <Button
            variant="ghost"
            size="xs"
            className="rounded-none font-mono text-[10px] text-destructive hover:text-destructive"
          >
            Stop
          </Button>
        </div>
      </div>
    </div>
  )

  const renderFilterChip = (label: string, value: HealthFilter, count: number) => (
    <button
      key={value}
      onClick={() => setHealthFilter(value)}
      className={cn(
        'flex items-center gap-1.5 px-2.5 py-1 text-[12px] border transition-colors',
        healthFilter === value
          ? 'border-border bg-muted text-foreground'
          : 'border-transparent text-muted-foreground/60 hover:text-muted-foreground',
      )}
    >
      {value === 'online' && <span className="size-1.5 rounded-full bg-emerald-500" />}
      {value === 'offline' && <span className="size-1.5 rounded-full bg-red-500" />}
      {label}
      <span className={cn(
        'font-mono text-[10px]',
        healthFilter === value ? 'text-muted-foreground' : 'text-muted-foreground/40',
      )}>
        {count}
      </span>
    </button>
  )

  const renderAdapterRow = (adapter: AdapterItem) => (
    <div
      key={adapter.type}
      className="flex items-center gap-3 border border-border/60 px-4 py-2.5 transition-colors hover:bg-muted/20"
    >
      {/* Name — flex-1 */}
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="text-[13px] font-semibold leading-none">{adapter.name}</span>
        <span className="font-mono text-[10px] text-muted-foreground/50 mt-0.5 leading-none">{adapter.type}</span>
      </div>

      {/* Health — w-24 */}
      <div className="flex w-24 shrink-0 items-center gap-1.5">
        {adapter.healthy ? (
          <>
            <Wifi className="size-3 text-emerald-500" />
            <span className="text-[12px] text-emerald-600 dark:text-emerald-400">Online</span>
          </>
        ) : (
          <>
            <WifiOff className="size-3 text-red-500" />
            <span className="text-[12px] text-red-600 dark:text-red-400">Offline</span>
          </>
        )}
      </div>

      {/* Default model — w-64 */}
      <div className="w-64 shrink-0">
        <span className="font-mono text-[11px] text-muted-foreground">{adapter.defaultModel || '—'}</span>
      </div>
    </div>
  )

  const renderTable = () => (
    <div className="flex flex-col gap-1.5 p-4">
      {/* Header card */}
      <div className="flex items-center gap-3 border border-border/40 bg-muted/20 px-4 py-1.5">
        <div className="flex-1 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">ADAPTER</div>
        <div className="w-24 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">HEALTH</div>
        <div className="w-64 shrink-0 font-mono text-[10px] font-bold tracking-widest text-muted-foreground/50">DEFAULT MODEL</div>
      </div>

      {filteredAdapters.length === 0 ? (
        <div className="py-8 text-center">
          <span className="font-mono text-[10px] text-muted-foreground/50">NO ADAPTERS MATCH</span>
        </div>
      ) : (
        filteredAdapters.map(renderAdapterRow)
      )}
    </div>
  )

  const renderMain = () => {
    if (isLoading) {
      return (
        <div className="flex flex-1 flex-col items-center justify-center gap-2">
          <Loader2 className="size-4 animate-spin text-muted-foreground" />
          <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">
            LOADING…
          </span>
        </div>
      )
    }
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {info && renderDaemonCard(info)}
        {renderTable()}
      </div>
    )
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-dashed border-border/60 px-4 py-1 bg-muted/20">
        <div className="flex items-center gap-2.5">
          <h1 className="text-lg font-semibold tracking-tight">Runtime</h1>
          {!isLoading && (
            <span className="font-mono text-[10px] font-bold tracking-widest text-muted-foreground/60">
              [{String(adapters.length).padStart(2, '0')}]
            </span>
          )}
        </div>
      </div>

      {!isLoading && (
        <div className="flex items-center gap-2 border-b border-border/40 px-4 py-1.5">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 size-3 text-muted-foreground/50" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search adapters..."
              className="h-6 rounded-none border-border/60 pl-6 text-xs w-44 bg-background"
            />
          </div>
          <div className="h-3.5 w-px bg-border/60" />
          <div className="flex items-center">
            {renderFilterChip('All', 'all', adapters.length)}
            {renderFilterChip('Online', 'online', onlineCount)}
            {renderFilterChip('Offline', 'offline', offlineCount)}
          </div>
        </div>
      )}

      {renderMain()}
    </div>
  )
}
