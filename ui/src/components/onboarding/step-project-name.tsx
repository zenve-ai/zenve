import { Input } from '@/components/ui/input'
import { Field, FieldGroup, FieldLabel, FieldError } from '@/components/ui/field'

interface StepProjectNameProps {
  projectName: string
  projectDescription: string
  nameError: string | null
  onNameChange: (value: string) => void
  onDescriptionChange: (value: string) => void
}

export function StepProjectName({
  projectName,
  projectDescription,
  nameError,
  onNameChange,
  onDescriptionChange,
}: StepProjectNameProps) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="font-mono text-[10px] tracking-widest uppercase text-muted-foreground/50">
          Step 01 / 04
        </p>
        <h2 className="mt-1 text-lg font-semibold leading-tight">Name your project</h2>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Choose a name for your project. You can change this later.
        </p>
      </div>

      <FieldGroup>
        <Field>
          <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
            Project name <span className="text-destructive">*</span>
          </FieldLabel>
          <Input
            className="rounded-none"
            placeholder="e.g. my-app"
            value={projectName}
            onChange={(e) => onNameChange(e.target.value)}
            aria-invalid={!!nameError}
            autoFocus
          />
          {nameError && <FieldError>{nameError}</FieldError>}
        </Field>

        <Field>
          <FieldLabel className="text-[11px] font-mono tracking-widest uppercase text-muted-foreground/70">
            Description <span className="text-muted-foreground/40">(optional)</span>
          </FieldLabel>
          <textarea
            className="w-full rounded-none border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 resize-none min-h-[80px]"
            placeholder="A short description of your project…"
            value={projectDescription}
            onChange={(e) => onDescriptionChange(e.target.value)}
          />
        </Field>
      </FieldGroup>
    </div>
  )
}
