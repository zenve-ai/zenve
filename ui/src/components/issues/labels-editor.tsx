import { useRef, useState } from 'react'
import { Check, Plus, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useListLabelsQuery } from '@/store/issues'

interface Props {
  workspaceId: string
  labels: string[]
  onUpdate: (labels: string[]) => void
  disabled?: boolean
}

export function LabelsEditor({ workspaceId, labels, onUpdate, disabled }: Props) {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: availableLabels = [] } = useListLabelsQuery({ workspaceId }, { skip: !open })

  const allKnown = Array.from(new Set([...availableLabels, ...labels])).sort()
  const filtered = input.trim()
    ? allKnown.filter((l) => l.toLowerCase().includes(input.toLowerCase()))
    : allKnown
  const inputVal = input.trim()
  const canCreate = inputVal.length > 0 && !allKnown.some((l) => l.toLowerCase() === inputVal.toLowerCase())

  const toggle = (label: string) => {
    if (labels.includes(label)) {
      onUpdate(labels.filter((l) => l !== label))
    } else {
      onUpdate([...labels, label])
    }
  }

  const create = () => {
    if (!canCreate) return
    onUpdate([...labels, inputVal])
    setInput('')
    inputRef.current?.focus()
  }

  const remove = (label: string, e: React.MouseEvent) => {
    e.stopPropagation()
    onUpdate(labels.filter((l) => l !== label))
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild disabled={disabled}>
        <div
          className={cn(
            'flex min-h-[24px] w-full cursor-pointer flex-wrap items-center gap-1',
            disabled && 'pointer-events-none opacity-40',
          )}
        >
          {labels.length === 0 ? (
            <span className="flex items-center gap-1 font-mono text-[11px] text-muted-foreground/40 hover:text-muted-foreground">
              <Plus className="size-3" />
              Add label
            </span>
          ) : (
            <>
              {labels.map((label) => (
                <span
                  key={label}
                  className="inline-flex items-center gap-1 border border-dashed border-border px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                >
                  {label}
                  <button
                    onClick={(e) => remove(label, e)}
                    className="text-muted-foreground/40 hover:text-foreground"
                  >
                    <X className="size-2.5" />
                  </button>
                </span>
              ))}
              <Plus className="size-3 text-muted-foreground/30 hover:text-muted-foreground" />
            </>
          )}
        </div>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={6}
        className="w-56 rounded-none border border-border p-0 shadow-md"
        onOpenAutoFocus={(e) => { e.preventDefault(); inputRef.current?.focus() }}
      >
        {/* Search / create input */}
        <div className="border-b border-border px-3 py-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') create()
              if (e.key === 'Escape') setOpen(false)
            }}
            placeholder="Search or create…"
            className="w-full bg-transparent font-mono text-[11px] placeholder:text-muted-foreground/40 focus:outline-none"
          />
        </div>

        {/* Existing labels */}
        {filtered.length > 0 && (
          <ul className="max-h-48 overflow-y-auto py-1">
            {filtered.map((label) => {
              const active = labels.includes(label)
              return (
                <li key={label}>
                  <button
                    onClick={() => toggle(label)}
                    className="flex w-full items-center gap-2 px-3 py-1.5 hover:bg-muted/50"
                  >
                    <span className={cn('size-3 shrink-0', active ? 'text-foreground' : 'text-transparent')}>
                      <Check className="size-3" />
                    </span>
                    <span className="min-w-0 flex-1 truncate text-left font-mono text-[11px]">{label}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}

        {/* Create new */}
        {canCreate && (
          <div className="border-t border-border">
            <button
              onClick={create}
              className="flex w-full items-center gap-2 px-3 py-1.5 hover:bg-muted/50"
            >
              <Plus className="size-3 shrink-0 text-muted-foreground" />
              <span className="font-mono text-[11px]">
                Create <span className="font-bold">"{inputVal}"</span>
              </span>
            </button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
