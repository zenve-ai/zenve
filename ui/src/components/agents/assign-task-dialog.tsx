import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export function AssignTaskDialog({
  open,
  onOpenChange,
  onSubmit,
  isSubmitting,
  agentName,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (message: string) => void
  isSubmitting: boolean
  agentName: string
}) {
  const [message, setMessage] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = message.trim()
    if (!trimmed) return
    onSubmit(trimmed)
  }

  const handleOpenChange = (next: boolean) => {
    if (!next) setMessage('')
    onOpenChange(next)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent showCloseButton>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Assign task</DialogTitle>
            <DialogDescription>
              Send a message to {agentName}. A new run will be queued for this agent.
            </DialogDescription>
          </DialogHeader>
          <FieldGroup className="gap-4 py-2">
            <Field>
              <FieldLabel htmlFor="assign-task-message">Task message</FieldLabel>
              <FieldDescription>Describe what you want the agent to do.</FieldDescription>
              <FieldContent>
                <Input
                  id="assign-task-message"
                  name="message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="e.g. Summarize open PRs and list blockers"
                  autoComplete="off"
                  disabled={isSubmitting}
                  className={cn('rounded-none')}
                />
              </FieldContent>
            </Field>
          </FieldGroup>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              size="xs"
              className="rounded-none"
              disabled={isSubmitting}
              onClick={() => handleOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              size="xs"
              className="rounded-none"
              disabled={isSubmitting || !message.trim()}
            >
              {isSubmitting ? 'Starting…' : 'Start run'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
