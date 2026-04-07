import * as React from "react"
import { cn } from "@/lib/utils"

function FieldGroup({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="field-group"
      className={cn("flex flex-col gap-4", className)}
      {...props}
    />
  )
}

function Field({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="field"
      className={cn("flex flex-col gap-2", className)}
      {...props}
    />
  )
}

function FieldLabel({
  className,
  htmlFor,
  children,
  ...props
}: React.ComponentProps<"label"> & { htmlFor?: string }) {
  return (
    <label
      data-slot="field-label"
      htmlFor={htmlFor}
      className={cn(
        "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        className
      )}
      {...props}
    >
      {children}
    </label>
  )
}

function FieldDescription({
  className,
  ...props
}: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="field-description"
      className={cn("text-muted-foreground text-sm", className)}
      {...props}
    />
  )
}

function FieldMessage({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="field-message"
      className={cn("text-destructive text-sm font-medium", className)}
      {...props}
    />
  )
}

function FieldSeparator({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="field-separator"
      className={cn("relative flex items-center gap-3 text-sm", className)}
      {...props}
    >
      <div className="h-px flex-1 bg-border" />
      <span
        data-slot="field-separator-content"
        className="text-muted-foreground"
      >
        {children}
      </span>
      <div className="h-px flex-1 bg-border" />
    </div>
  )
}

export {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldMessage,
  FieldSeparator,
}
