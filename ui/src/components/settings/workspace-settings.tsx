import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { toast } from 'sonner'
import { GitBranch, Layers, MessageSquare, FileText, Database } from 'lucide-react'
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { SettingsSection } from './settings-section'
import { SettingsItem } from './settings-item'
import { useGetWorkspaceSettingsQuery, useUpdateWorkspaceSettingsMutation } from '@/store/workspace'
import { useGetGlobalSettingsQuery } from '@/store/settings'
import type { WorkspaceSettingsUpdate } from '@/types'

function SkeletonField() {
  return (
    <div className="flex flex-col gap-1.5">
      <Skeleton className="h-3 w-24 rounded-none" />
      <Skeleton className="h-9 w-full rounded-none" />
    </div>
  )
}

export function WorkspaceSettings() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const { data: settings, isLoading } = useGetWorkspaceSettingsQuery(workspaceId!, { skip: !workspaceId })
  const { data: globalSettings } = useGetGlobalSettingsQuery()
  const [update, { isLoading: isSaving }] = useUpdateWorkspaceSettingsMutation()

  const [form, setForm] = useState({
    description: '',
    default_branch: 'main',
    commit_message_prefix: '[zenve]',
    run_timeout_seconds: 600,
    stack: '',
    issues_adapter: '',
  })

  useEffect(() => {
    if (settings) {
      setForm({
        description: settings.description,
        default_branch: settings.default_branch,
        commit_message_prefix: settings.commit_message_prefix,
        run_timeout_seconds: settings.run_timeout_seconds,
        stack: settings.stack.join(', '),
        issues_adapter: settings.issues.adapter ?? '',
      })
    }
  }, [settings])

  const set = (key: string, value: string | number) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const handleSave = async () => {
    if (!workspaceId) return
    const body: WorkspaceSettingsUpdate = {
      description: form.description,
      default_branch: form.default_branch,
      commit_message_prefix: form.commit_message_prefix,
      stack: form.stack.split(',').map((s) => s.trim()).filter(Boolean),
      issues: { adapter: form.issues_adapter || null },
    }
    try {
      await update({ id: workspaceId, body }).unwrap()
      toast.success('Workspace settings saved')
    } catch {
      toast.error('Failed to save settings')
    }
  }

  const renderLoading = () => (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-4 w-3/4 rounded-none" />
      <div className="flex flex-col gap-4">
        <SkeletonField />
        <SkeletonField />
        <SkeletonField />
      </div>
    </div>
  )


  const renderForm = () => (
    <div className="flex flex-col gap-6">
      <SettingsSection label="Workspace">
        <SettingsItem
          icon={<FileText className="h-3.5 w-3.5 text-muted-foreground/60" />}
          title={settings?.slug ?? '—'}
          description="Workspace slug — edit .zenve/settings.json directly to rename"
        />
      </SettingsSection>

      <SettingsSection label="Configuration">
        <div className="flex flex-col gap-4 p-4">
          <FieldGroup>
            <Field>
              <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
                Description
              </FieldLabel>
              <textarea
                className="w-full rounded-none border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 resize-none min-h-[72px]"
                placeholder="A short description of this workspace…"
                value={form.description}
                onChange={(e) => set('description', e.target.value)}
              />
            </Field>

            <Field>
              <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
                <GitBranch className="h-3 w-3" /> Default branch
              </FieldLabel>
              <Input
                className="rounded-none font-mono text-[12px]"
                placeholder="main"
                value={form.default_branch}
                onChange={(e) => set('default_branch', e.target.value)}
              />
            </Field>

            <Field>
              <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
                <MessageSquare className="h-3 w-3" /> Commit message prefix
              </FieldLabel>
              <Input
                className="rounded-none font-mono text-[12px]"
                placeholder="[zenve]"
                value={form.commit_message_prefix}
                onChange={(e) => set('commit_message_prefix', e.target.value)}
              />
            </Field>

            {/* Run timeout — not yet surfaced in the UI
            <Field>
              <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
                <Timer className="h-3 w-3" /> Run timeout (seconds)
              </FieldLabel>
              <Input
                className="rounded-none font-mono text-[12px]"
                type="number"
                min={60}
                placeholder="600"
                value={form.run_timeout_seconds}
                onChange={(e) => set('run_timeout_seconds', e.target.value)}
              />
            </Field>
            */}

            <Field>
              <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
                <Layers className="h-3 w-3" /> Stack
              </FieldLabel>
              <Input
                className="rounded-none font-mono text-[12px]"
                placeholder="react, typescript, tailwind"
                value={form.stack}
                onChange={(e) => set('stack', e.target.value)}
              />
              <p className="font-mono text-[10px] text-muted-foreground/50">Comma-separated list</p>
            </Field>

            <Field>
              <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
                <Database className="h-3 w-3" /> Issues adapter
              </FieldLabel>
              <Select value={form.issues_adapter || 'inherit'} onValueChange={(v) => set('issues_adapter', v === 'inherit' ? '' : v)}>
                <SelectTrigger className="w-48 rounded-none text-[12px] font-mono">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="inherit">inherit ({globalSettings?.issues_adapter ?? 'github'})</SelectItem>
                  <SelectItem value="github">github</SelectItem>
                  <SelectItem value="sqlite">sqlite</SelectItem>
                </SelectContent>
              </Select>
              <p className="font-mono text-[10px] text-muted-foreground/50">
                Override the global issues adapter for this workspace
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
