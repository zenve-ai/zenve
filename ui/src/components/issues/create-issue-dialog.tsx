import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Field,
  FieldContent,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (title: string, body: string) => void
  isSubmitting: boolean
}

export function CreateIssueDialog({ open, onOpenChange, onSubmit, isSubmitting }: Props) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const t = title.trim()
    if (!t) return
    onSubmit(t, body.trim())
  }

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setTitle('')
      setBody('')
    }
    onOpenChange(next)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent showCloseButton>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>New issue</DialogTitle>
          </DialogHeader>
          <FieldGroup className="gap-4 py-2">
            <Field>
              <FieldLabel htmlFor="issue-title">Title</FieldLabel>
              <FieldContent>
                <Input
                  id="issue-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Short, descriptive title"
                  autoComplete="off"
                  disabled={isSubmitting}
                  className={cn('rounded-none')}
                />
              </FieldContent>
            </Field>
            <Field>
              <FieldLabel htmlFor="issue-body">Description</FieldLabel>
              <FieldContent>
                <textarea
                  id="issue-body"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="Optional description..."
                  rows={5}
                  disabled={isSubmitting}
                  className="w-full resize-none border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground/40 focus:border-ring focus:outline-none disabled:opacity-50"
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
              disabled={isSubmitting || !title.trim()}
            >
              {isSubmitting ? 'Creating…' : 'Create issue'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
