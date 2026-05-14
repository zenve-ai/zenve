import { Input } from '@/components/ui/input'
import { Field, FieldGroup, FieldLabel, FieldError } from '@/components/ui/field'

interface StepWorkspaceProps {
  name: string
  description: string
  path: string
  nameError: string | null
  pathError: string | null
  onNameChange: (value: string) => void
  onDescriptionChange: (value: string) => void
  onPathChange: (value: string) => void
}

export function StepWorkspace({
  name,
  description,
  path,
  nameError,
  pathError,
  onNameChange,
  onDescriptionChange,
  onPathChange,
}: StepWorkspaceProps) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/50">
          Step 01 / 03
        </p>
        <h2 className="mt-1 text-lg font-semibold leading-tight">Define your workspace</h2>
        <p className="mt-1 text-[13px] text-muted-foreground">
          A workspace is a local directory containing a <code className="font-mono text-[12px]">.zenve/</code> folder.
        </p>
      </div>

      <FieldGroup>
        <Field>
          <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
            Workspace name <span className="text-destructive">*</span>
          </FieldLabel>
          <Input
            className="rounded-none"
            placeholder="e.g. my-app"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            aria-invalid={!!nameError}
            autoFocus
          />
          {nameError && <FieldError>{nameError}</FieldError>}
        </Field>

        <Field>
          <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
            Path <span className="text-destructive">*</span>
          </FieldLabel>
          <Input
            className="rounded-none font-mono text-[12px]"
            placeholder="/absolute/path/to/repo"
            value={path}
            onChange={(e) => onPathChange(e.target.value)}
            aria-invalid={!!pathError}
          />
          {pathError && <FieldError>{pathError}</FieldError>}
        </Field>

        <Field>
          <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
            Description <span className="text-muted-foreground/40">(optional)</span>
          </FieldLabel>
          <textarea
            className="w-full rounded-none border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 resize-none min-h-[80px]"
            placeholder="A short description of this workspace…"
            value={description}
            onChange={(e) => onDescriptionChange(e.target.value)}
          />
        </Field>
      </FieldGroup>
    </div>
  )
}
