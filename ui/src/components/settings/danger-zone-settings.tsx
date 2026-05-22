import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { SettingsSection } from './settings-section'
import { SettingsItem } from './settings-item'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { useUnregisterWorkspaceMutation } from '@/store/workspace'
import { toast } from 'sonner'
import { Loader2, Trash2 } from 'lucide-react'

export function DangerZoneSettings() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [unregister, { isLoading }] = useUnregisterWorkspaceMutation()

  const handleUnregister = async () => {
    if (!workspaceId) return
    try {
      await unregister(workspaceId).unwrap()
      toast.success('Workspace unregistered')
      setOpen(false)
      navigate('/')
    } catch {
      toast.error('Failed to unregister workspace')
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="font-mono text-[11px] leading-relaxed text-muted-foreground/60">
        These actions are permanent. Your repository files on disk are not deleted.
      </p>

      <SettingsSection label="Destructive actions">
        <SettingsItem
          icon={<Trash2 className="h-3.5 w-3.5 text-destructive/60" />}
          title="Unregister workspace"
          description="Removes this workspace from the Zenve runtime. Agents stop running immediately. Your repo files are not affected."
          action={
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button variant="destructive" size="xs" className="rounded-none">
                  Unregister
                </Button>
              </DialogTrigger>
              <DialogContent className="rounded-none">
                <DialogHeader>
                  <DialogTitle>Unregister workspace?</DialogTitle>
                  <DialogDescription>
                    This removes the workspace from the Zenve runtime. Agents will stop running and no new runs will be triggered. Your repository files on disk are not affected.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button
                    variant="outline"
                    size="xs"
                    className="rounded-none"
                    onClick={() => setOpen(false)}
                    disabled={isLoading}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    size="xs"
                    className="rounded-none"
                    onClick={handleUnregister}
                    disabled={isLoading}
                  >
                    {isLoading && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />}
                    Unregister
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          }
        />
      </SettingsSection>
    </div>
  )
}
