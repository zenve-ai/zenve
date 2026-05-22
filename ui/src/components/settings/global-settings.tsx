import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Database } from 'lucide-react'
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { SettingsSection } from './settings-section'
import { useGetGlobalSettingsQuery, useUpdateGlobalSettingsMutation } from '@/store/settings'

export function GlobalSettings() {
  const { data: settings, isLoading } = useGetGlobalSettingsQuery()
  const [update, { isLoading: isSaving }] = useUpdateGlobalSettingsMutation()

  const [issuesAdapter, setIssuesAdapter] = useState('github')

  useEffect(() => {
    if (settings) setIssuesAdapter(settings.issues_adapter)
  }, [settings])

  const handleSave = async () => {
    try {
      await update({ issues_adapter: issuesAdapter }).unwrap()
      toast.success('Settings saved')
    } catch {
      toast.error('Failed to save settings')
    }
  }

  const renderLoading = () => (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-4 w-2/3 rounded-none" />
      <div className="border border-dashed border-border-visible">
        <div className="flex flex-col gap-4 p-4">
          <div className="flex flex-col gap-1.5">
            <Skeleton className="h-3 w-24 rounded-none" />
            <Skeleton className="h-9 w-40 rounded-none" />
          </div>
        </div>
      </div>
    </div>
  )

  const renderForm = () => (
    <div className="flex flex-col gap-6">
      <SettingsSection label="Runtime">
        <div className="flex flex-col gap-4 p-4">
          <FieldGroup>
            <Field>
              <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
                <Database className="h-3 w-3" /> Issues adapter
              </FieldLabel>
              <Select value={issuesAdapter} onValueChange={setIssuesAdapter}>
                <SelectTrigger className="w-40 rounded-none text-[12px] font-mono">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="github">github</SelectItem>
                  <SelectItem value="sqlite">sqlite</SelectItem>
                </SelectContent>
              </Select>
              <p className="font-mono text-[10px] text-muted-foreground/50">
                github — live issues via GitHub API · sqlite — local database
              </p>
            </Field>
          </FieldGroup>

          <div className="flex justify-end pt-2">
            <Button
              size="xs"
              className="rounded-none"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </div>
      </SettingsSection>
    </div>
  )

  const renderMain = () => {
    if (isLoading) return renderLoading()
    return renderForm()
  }

  return renderMain()
}
